"""Developer-local PRD 14.1 measurements; never a timing gate or optimizer.

Run with python3 -B sbtd-runtime/tests/runtime_perf.py --events 10000 --output DIR.
The seed deadline may reduce the actual dataset; reports never extrapolate it.
No SQL inserts, validation bypasses, renderer substitutes or dependency installs.
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import http.client
import json
import math
import os
import platform
import re
import shlex
import shutil
import stat
import subprocess
import sys
import tempfile
import threading
import time
from collections import Counter
from datetime import UTC, datetime, timedelta
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))

from event_store import EventStore
from export_render import load_panel_manifest
from history_read import list_events, paginate
from test_serve import ServeProcess, _enable_observation, _free_port

END = datetime(2026, 10, 25, tzinfo=UTC)
FORMATS = ("html", "csv", "jpeg", "pdf")


def distribution(values: list[float]) -> dict:
    ordered = sorted(values)
    return {
        "n": len(ordered),
        "p50": ordered[math.ceil(len(ordered) * 0.5) - 1] if ordered else None,
        "p95": ordered[math.ceil(len(ordered) * 0.95) - 1] if ordered else None,
        "max": max(ordered) if ordered else None,
        "samples": values,
    }


def measurement(
    values: list[float], target: float, *, eligible=True, reason=""
) -> dict:
    result = distribution(values)
    result.update(target_seconds=target, reason=reason)
    result["status"] = (
        ("met" if result["p95"] <= target else "not-met")
        if values and eligible
        else "not-measured"
    )
    return result


def event_at(index: int, templates: dict) -> dict:
    """Each complete 100-event block: one task, ten paired steps, 79 transitions."""
    block, slot = divmod(index, 100)
    kind = "task.created" if slot == 0 else "task.state_changed"
    if 1 <= slot <= 20:
        kind = "step.started" if slot % 2 else "step.finished"
    event = copy.deepcopy(templates[kind])
    identity = f"perf-{index:09d}"
    event.update(event_id=identity, ingest_seq=index + 1)
    instant = END - timedelta(days=7 - block % 7) + timedelta(seconds=slot)
    event["occurred_at"] = event["recorded_at"] = instant.isoformat()
    event["provenance"]["source_event_id"] = identity
    scope = event["scope"]
    scope.update(
        task_uid=f"perf-task-{block:06d}",
        logical_task_id=f"synthetic/{block:06d}",
        task_run_id=f"perf-run-{block:06d}" if kind.startswith("step.") else None,
        step_run_id=f"perf-step-{block:06d}-{(slot + 1) // 2:02d}"
        if kind.startswith("step.")
        else None,
    )
    return event


def seed(home: Path, requested: int, seconds: float) -> dict:
    source = json.loads((RUNTIME / "golden/dataset.json").read_text(encoding="utf-8"))
    templates = {event["event_type"]: event for event in source["events"]}
    _enable_observation(home)
    start = time.perf_counter()
    actual = 0
    sizes = Counter()
    digest = hashlib.sha256()
    writes = []
    with EventStore.open(home, confirmed=True) as store:
        while actual < requested and time.perf_counter() - start < seconds:
            # Small batches bound the existing spool concatenation cost; every
            # event still takes the public validation/fsync/dedup/commit path.
            batch = [
                event_at(i, templates)
                for i in range(actual, min(actual + 100, requested))
            ]
            for event in batch:
                payload = json.dumps(event, sort_keys=True, ensure_ascii=False).encode()
                sizes[len(payload)] += 1
                digest.update(payload + b"\n")
            before = time.perf_counter()
            result = store.append(batch)
            writes.append(time.perf_counter() - before)
            if any(outcome.status != "accepted" for outcome in result.outcomes):
                raise AssertionError("synthetic event rejected or deduplicated")
            actual += len(batch)
        quality = store.quality()
        assert quality.accepted == actual
    if actual == 0:
        raise ValueError("seed deadline allowed no events")
    return {
        "requested_events": requested,
        "events": actual,
        "tasks": (actual + 99) // 100,
        "steps": sum(
            min(10, max(0, (actual - b * 100) // 2))
            for b in range((actual + 99) // 100)
        ),
        "seed_seconds": time.perf_counter() - start,
        "seed_limit_seconds": seconds,
        "batch_append_seconds": distribution(writes),
        "event_json_bytes_histogram": dict(sorted(sizes.items())),
        "input_sha256": digest.hexdigest(),
        "path": "EventStore.append batches <=100; all validations, spool fsync and per-event SQL commits retained",
        "time_distribution": "100-event blocks cycle over seven UTC days; fixed end 2026-10-25T00:00:00Z",
        "truncated": actual != requested,
        "database_bytes": (home / "audit.db").stat().st_size,
    }


def scope(days: int, offset: int = 0) -> dict:
    manifest = load_panel_manifest()
    return {
        "schema_version": "1.0",
        "range": {
            "from": (END - timedelta(days=days)).isoformat(),
            "to": (END + timedelta(microseconds=offset)).isoformat(),
            "timezone": "UTC",
        },
        "metrics": sorted(
            {m for panel in manifest["panels"] for m in panel["metric_ids"]}
        ),
    }


class Client:
    def __init__(self, port: int, requests: list):
        self.port = port
        self.headers = {}
        self.requests = requests
        self.secrets = []
        self.scanned_artifacts = 0

    def call(self, method: str, path: str, body=None, *, expected=200, target=None):
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=300)
        headers = {**self.headers, "Content-Type": "application/json"}
        try:
            connection.request(
                method, path, json.dumps(body) if body is not None else None, headers
            )
            response = connection.getresponse()
            self.requests.append(
                {"method": method, "path": path, "status": response.status}
            )
            if response.status != expected:
                response.read()
                raise RuntimeError(
                    f"{method} {path}: HTTP {response.status}, expected {expected}"
                )
            if target is not None:
                needles = [value.encode() for value in self.secrets] + [b"#ticket="]
                overlap = max(map(len, needles))
                previous = b""
                with target.open("wb") as handle:
                    while chunk := response.read(1024 * 1024):
                        assert not any(
                            value in previous + chunk for value in needles
                        ), "credential in export"
                        previous = chunk[-overlap:]
                        handle.write(chunk)
                self.scanned_artifacts += 1
                return None
            data = response.read()
            if path == "/api/v1/session/pair":
                session = json.loads(data)
                self.secrets.extend(
                    [
                        self.headers["X-Pairing-Code"],
                        session["access_token"],
                        response.getheader("x-csrf-token"),
                    ]
                )
                self.headers = {
                    "Authorization": f"Bearer {session['access_token']}",
                    "X-CSRF-Token": response.getheader("x-csrf-token"),
                }
                return None
            return json.loads(data)
        finally:
            connection.close()


def quota_usage(home: Path) -> tuple[int, int]:
    total = temporary = 0
    for name in ("snapshots", "exports"):
        directory = home / name
        if not directory.exists():
            continue
        for path in directory.iterdir():
            try:
                info = path.lstat()
            except FileNotFoundError:
                continue
            if stat.S_ISREG(info.st_mode):
                total += info.st_size
                if path.name.startswith((".snapshot-", ".export-")):
                    temporary += info.st_size
    return total, temporary


class Monitor:
    """Sampled lower bounds, not claimed hard resource limits or child-tree RSS."""

    def __init__(self, home: Path, pid: int):
        self.home, self.pid = home, pid
        self.stop = threading.Event()
        self.peak_bytes = self.temp_bytes = 0
        self.rss_bytes = None
        self.thread = threading.Thread(target=self.run, daemon=True)

    def run(self):
        while not self.stop.is_set():
            total, temporary = quota_usage(self.home)
            self.peak_bytes = max(self.peak_bytes, total)
            self.temp_bytes = max(self.temp_bytes, temporary)
            if sys.platform.startswith("linux"):
                try:
                    text = Path(f"/proc/{self.pid}/status").read_text()
                    match = re.search(r"^VmHWM:\s+(\d+) kB", text, re.MULTILINE)
                    if match:
                        self.rss_bytes = max(self.rss_bytes or 0, int(match[1]) * 1024)
                except FileNotFoundError:
                    pass
            self.stop.wait(0.02)

    def __enter__(self):
        self.thread.start()
        return self

    def __exit__(self, *_args):
        self.stop.set()
        self.thread.join()


def browser_measurements(
    client: Client, home: Path, samples: int, artifacts: Path
) -> dict:
    """Optional real browser; no installation, API mocks or renderer overrides."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            "ui_first_usable": measurement(
                [],
                3,
                reason="Playwright is not installed; separate MCP observation may supplement this run",
            )
        }
    from browser_renderer import _shell_executable

    executable = _shell_executable(home)
    if executable is None:
        return {
            "ui_first_usable": measurement(
                [],
                3,
                reason="pinned Chromium shell unavailable; no substitute installed",
            )
        }
    values = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(executable), headless=True
        )
        try:
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            credentials = {
                "bearer": client.headers["Authorization"].removeprefix("Bearer "),
                "csrf": client.headers["X-CSRF-Token"],
            }
            page.add_init_script(
                "sessionStorage.setItem('sbtd.session', "
                + json.dumps(json.dumps(credentials))
                + ")"
            )
            for _ in range(samples):
                start = time.perf_counter()
                page.goto(
                    f"http://127.0.0.1:{client.port}/", wait_until="domcontentloaded"
                )
                page.wait_for_function(
                    "() => document.querySelectorAll('[data-panel-id]').length === 13 && document.querySelectorAll('.panel-metric').length > 0",
                    timeout=300_000,
                )
                values.append(time.perf_counter() - start)
            page.close()
            page = browser.new_page(viewport={"width": 1440, "height": 900})
            page.set_content((artifacts / "sample-0.html").read_text(encoding="utf-8"))
            page.evaluate("() => document.fonts.ready")
            geometry = page.evaluate(
                "() => ({height: document.documentElement.scrollHeight, width: innerWidth, panels: document.querySelectorAll('section.panel').length})"
            )
            return {
                "ui_first_usable": measurement(
                    values,
                    3,
                    reason="real pinned Chromium; pre-paired; current 24h scope; navigation until 13 rendered core Panels",
                ),
                "geometry": geometry,
                "browser_version": browser.version,
            }
        finally:
            browser.close()


def exercise(home: Path, samples: int, report: dict, artifacts: Path) -> None:
    report["requests"] = []
    metrics = report["measurements"] = {}
    port = _free_port()
    server = ServeProcess(home, port, "--no-open")
    client = Client(port, report["requests"])
    try:
        server.wait_ready(timeout=60)
        client.headers["X-Pairing-Code"] = (home / "pairing-ticket").read_text().strip()
        client.call("POST", "/api/v1/session/pair")
        with Monitor(home, server.proc.pid) as monitor:
            chosen = None
            for days in (1, 7):
                for temperature in ("cold", "hot"):
                    values = []
                    ids = []
                    for sample in range(samples):
                        # Cold means unique scope, no matching snapshot. OS page
                        # cache is NOT flushed. Hot repeats the last cold scope.
                        offset = sample + 1 if temperature == "cold" else samples
                        before = time.perf_counter()
                        answer = client.call(
                            "POST", "/api/v1/statistics/query", scope(days, offset)
                        )["data"]
                        values.append(time.perf_counter() - before)
                        ids.append(answer["snapshot_id"])
                    assert (
                        (len(set(ids)) == samples)
                        if temperature == "cold"
                        else (len(set(ids)) == 1)
                    )
                    metrics[f"query_{days}d_{temperature}"] = measurement(
                        values, 3 if temperature == "cold" else 1
                    )
                    chosen = ids[-1]
            snapshot = client.call("GET", f"/api/v1/report-snapshots/{chosen}")["data"]
            report["snapshot_manifest"] = snapshot
            (artifacts / "snapshot-manifest.json").write_text(
                json.dumps(snapshot, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            snapshot_bytes = (home / "snapshots" / f"{chosen}.json").stat().st_size
            report["capacity"] = {"snapshot_bytes": snapshot_bytes, "exports": {}}
            formats = client.call("GET", "/api/v1/capabilities")["data"]["exports"]
            report["capabilities"] = formats
            for format_name in FORMATS:
                client.headers["Idempotency-Key"] = f"perf-{format_name}-unavailable"
                if not formats[format_name]["available"]:
                    client.call(
                        "POST",
                        "/api/v1/exports",
                        {"snapshot_id": chosen, "format": format_name},
                        expected=503,
                    )
                    metrics[f"export_{format_name}"] = measurement(
                        [], 20, reason=formats[format_name]["reason"]
                    )
                    report["capacity"]["exports"][format_name] = {
                        "status": "unavailable",
                        "reason": formats[format_name]["reason"],
                    }
                    continue
                values, byte_counts = [], []
                for sample in range(samples):
                    client.headers["Idempotency-Key"] = f"perf-{format_name}-{sample}"
                    before = time.perf_counter()
                    created = client.call(
                        "POST",
                        "/api/v1/exports",
                        {"snapshot_id": chosen, "format": format_name},
                        expected=202,
                    )
                    export_id = created["data"]["export_id"]
                    deadline = time.monotonic() + 300
                    while True:
                        info = client.call("GET", f"/api/v1/exports/{export_id}")[
                            "data"
                        ]
                        if info["status"] == "ready":
                            break
                        if (
                            info["status"] not in ("queued", "generating")
                            or time.monotonic() >= deadline
                        ):
                            raise RuntimeError(
                                f"export {format_name}: {info['status']}"
                            )
                        time.sleep(0.05)
                    values.append(time.perf_counter() - before)
                    target = artifacts / f"sample-{sample}.{format_name}"
                    client.call(
                        "GET", f"/api/v1/exports/{export_id}/file", target=target
                    )
                    with target.open("rb") as handle:
                        digest = hashlib.file_digest(handle, "sha256").hexdigest()
                    assert (
                        target.stat().st_size == info["byte_size"]
                        and digest == info["sha256"]
                    )
                    byte_counts.append(
                        {
                            "artifact_bytes": info["byte_size"],
                            "manifest_bytes": (home / "exports" / f"{export_id}.json")
                            .stat()
                            .st_size,
                            "sha256": digest,
                            "renderer_version": info["renderer_version"],
                            "panel_ids": info["panel_ids"],
                        }
                    )
                    assert set(info["panel_ids"]) == {
                        panel["panel_id"] for panel in load_panel_manifest()["panels"]
                    }
                target_seconds = {"html": 5, "csv": 60, "jpeg": 20, "pdf": 20}[
                    format_name
                ]
                metrics[f"export_{format_name}"] = measurement(
                    values,
                    target_seconds,
                    eligible=format_name != "csv",
                    reason="CSV full-buffer implementation, not streaming; reference million rows not established"
                    if format_name == "csv"
                    else "13 panels, default 1440px presentation; CSS height needs browser measurement",
                )
                report["capacity"]["exports"][format_name] = {
                    "status": "measured",
                    "samples": byte_counts,
                }
                if format_name == "csv":
                    with (artifacts / "sample-0.csv").open(
                        encoding="utf-8-sig", newline=""
                    ) as handle:
                        report["csv_rows"] = dict(
                            Counter(
                                row["record_type"] for row in csv.DictReader(handle)
                            )
                        )
                if format_name == "html":
                    text = (artifacts / "sample-0.html").read_text(encoding="utf-8")
                    report["html_panel_count"] = text.count('class="panel"')
                    assert report["html_panel_count"] == len(
                        load_panel_manifest()["panels"]
                    )
            report["sensitive_scan"] = {
                "scanned_artifacts": client.scanned_artifacts,
                "matches": 0,
                "scope": "exact issued synthetic ticket, bearer, CSRF and ticket-URL marker; streamed downloads; not a general privacy certification",
            }
            browser = browser_measurements(client, home, samples, artifacts)
            metrics["ui_first_usable"] = browser.pop("ui_first_usable")
            report["browser"] = browser
            report["resources"] = {
                "serve_peak_rss_bytes": monitor.rss_bytes,
                "sampled_quota_peak_bytes": monitor.peak_bytes,
                "sampled_temp_peak_bytes": monitor.temp_bytes,
                "scope": "20ms samples; snapshot/export flat files only; RSS Linux VmHWM for serve, excludes renderer children; other OS RSS unavailable",
            }
    finally:
        if server.proc.poll() is None:
            try:
                _, _, code = server.stop()
                report["serve_exit"] = code
            except subprocess.TimeoutExpired:
                server.kill()
                report["serve_exit"] = "forced-kill-after-stop-timeout"

    values = []
    offset = 0
    cursor = None
    with EventStore.open(home, read_only=True) as store:
        for _ in range(samples):
            before = time.perf_counter()
            page = paginate(list_events(store.replay()), cursor=cursor, limit=100)
            values.append(time.perf_counter() - before)
            assert len(page["items"]) == min(100, page["total"] - offset)
            offset = offset + len(page["items"]) if page["next_cursor"] else 0
            cursor = page["next_cursor"]
    metrics["audit_100"] = measurement(
        values,
        0.5,
        reason="real EventStore.replay + history_read.list_events/paginate library path; full scan, not indexed HTTP audit",
    )
    metrics["audit_100"]["latency_status"] = metrics["audit_100"]["status"]
    metrics["audit_100"]["status"] = "not-met"
    metrics["audit_100"]["index_requirement"] = "not-met: replay and sort all events"
    metrics["export_csv"]["latency_status"] = (
        "met" if metrics["export_csv"]["p95"] <= 60 else "not-met"
    )
    metrics["export_csv"]["streaming_requirement"] = "not-met: full buffered generation"
    metrics["export_csv"]["reference_scale_status"] = (
        "measured"
        if report["csv_rows"].get("event", 0) >= 1_000_000
        else "not-measured"
    )
    source = json.loads((RUNTIME / "golden/dataset.json").read_text(encoding="utf-8"))
    templates = {event["event_type"]: event for event in source["events"]}
    writes = []
    # Exclude these extra latency probes from the measured snapshot/dataset.
    with EventStore.open(home, confirmed=True) as store:
        for i in range(20):
            event = event_at(report["dataset"]["events"] + i, templates)
            before = time.perf_counter()
            result = store.append([event])
            writes.append(time.perf_counter() - before)
            assert result.outcomes[0].status == "accepted"
    metrics["collection_append"] = measurement(
        writes,
        0.020,
        reason="public EventStore.append single event including validation/fsync/commit, excluding event construction; not full host SDK overhead",
    )
    for name, reason in {
        "event_to_visible": "by design 30-second polling, not measured; actual latency display not verified",
        "concurrency": "one export worker in code; concurrent pages not load-tested; ThreadPoolExecutor admission has no explicit queue count bound",
        "resource_limits": "sampled usage is not platform limit/cancellation verification",
    }.items():
        metrics[name] = measurement(
            [],
            {"ui_first_usable": 3, "event_to_visible": 30}.get(name, 0),
            reason=reason,
        )


def write_report(report: dict, output: Path, stem: str) -> Path:
    scale_note = ""
    if report.get("dataset", {}).get("requested_events", 1_000_000) < 1_000_000:
        report["reference_scale_note"] = (
            "未达 1M 档：请求事件数低于 1_000_000；本次结果不代表 1M 档通过。"
        )
        scale_note = f"\n规模说明：{report['reference_scale_note']}"
    raw = output / f"{stem}.json"
    raw.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    rows = []
    for name, item in report.get("measurements", {}).items():
        rows.append(
            f"| {name} | {item['n']} | {item['p50']} | {item['p95']} | {item['max']} | {item['status']} | {item['reason']} |"
        )
    requests = sorted(
        {(r["method"], r["path"], r["status"]) for r in report.get("requests", [])}
    )
    summary = f"""# 测试运行汇总：PR-4 性能与容量

## 执行结论

结论：{report["execution"]}；这是 developer-local 测量，不是产品性能通过或发布就绪。
实际规模：{json.dumps(report.get("dataset", {}), ensure_ascii=False)}{scale_note}

## 运行信息

时间：{report["created_at"]}；分支：{report["branch"]}；SHA：{report["source_revision"]}；dirty：{report["dirty"]}。
平台：{report["platform"]}；Python：{report["python"]}；逻辑 CPU：{report["logical_cpus"]}。
工作区：{report["worktree"]}；Evidence Publication：local-only；E2E Mode：backend-only；Mock Strategy：none；rtk：skipped-for-report。
参考机符合性须按实际 CPU／内存／磁盘与原生平台另行判断；本报告不自动认定参考机或 D9 人工验收。

## 运行命令

```sh
{report["command"]}
```

## 关联 BDD 与本轮范围

PRD §14.1／§18；沿用 r2.2-native-e2e-scenarios.md，不改变产品行为。
热查询复用最后冷查询 scope；冷查询改变结束时间微秒确保无快照复用，不清 OS 缓存，不包含启动时间。
导出从 POST 开始到 ready（包含 JPEG preflight、排队及 50ms 轮询），下载不计时；失败不会变成 unavailable。
p50／p95 使用 nearest-rank，单位秒，小样本不是稳定统计结论。met 仅当前规模与测量面，不等于 AC-62。

## 用例结果

| 项目 | n | p50 秒 | p95 秒 | max 秒 | 目标比较 | 边界 |
|---|---|---|---|---|---|---|
{chr(10).join(rows)}

## 失败、修复与复跑

本轮错误：{report.get("error", "无")}。不重试筛选成功，不优化产品。失败轮保留。

## 覆盖范围 → API URI

| Method | URI | 实际状态 |
|---|---|---|
{chr(10).join(f"| {method} | {path} | {status} |" for method, path, status in requests)}

## 产物与状态

原生报告：{raw.name}；同 stem 中文摘要；样本目录：{stem}-artifacts。
快照 public manifest、四格式可用样本、CSV 数据族计数和 SHA-256 见 raw／样本；不可用格式不造样本。
容量（st_size 字节）：{json.dumps(report.get("capacity", {}), ensure_ascii=False)}
资源：{json.dumps(report.get("resources", {}), ensure_ascii=False)}
Final Test Report／Run Summary MD：generated。测量执行成功不代表目标全部 met。

## 未执行项、风险与发布边界

D9 用户 Mac 人工视觉／字体、macOS 实机性能与 JPEG/PDF 字节数 pending。
Windows 本机未测；并发、故障上限与事件可见延迟未测。CSV 实现非流式，不用客户端分块下载冒充流式生成。
共享配额仅 snapshots/＋exports/，不包含 audit.db、浏览器、报告样本；20ms 临时文件峰值只是采样下界。
合成数据没有真实账号；未执行生产数据或敏感数据安全验收。仅本地证据，不发布、不关闭 R2.2。
"""
    (output / f"{stem}.md").write_text(summary, encoding="utf-8")
    return raw


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--events", type=int, default=10_000)
    parser.add_argument("--samples", type=int, default=3)
    parser.add_argument("--seed-seconds", type=float, default=900)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--renderer-home",
        type=Path,
        help="copy only browsers/ from an explicitly supplied existing runtime; no profiles or installation",
    )
    parser.add_argument(
        "--keep-home",
        action="store_true",
        help="retain only this run's synthetic home for browser follow-up",
    )
    args = parser.parse_args(argv)
    if min(args.events, args.samples, args.seed_seconds) <= 0:
        parser.error("events, samples and seed-seconds must be positive")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    repo = RUNTIME.parent

    def git(*command):
        return subprocess.check_output(["git", *command], cwd=repo, text=True).strip()

    now = datetime.now(UTC)
    branch = git("branch", "--show-current")
    stem = f"runtime-perf-{args.events}-{re.sub(r'[^a-zA-Z0-9._-]', '_', branch)}-{now.strftime('%Y%m%dT%H%M%S%fZ')}"
    artifacts = output / f"{stem}-artifacts"
    artifacts.mkdir()
    command = [
        "python3",
        "-B",
        "sbtd-runtime/tests/runtime_perf.py",
        *(sys.argv[1:] if argv is None else argv),
    ]
    report = {
        "created_at": now.isoformat(),
        "source_revision": git("rev-parse", "HEAD"),
        "dirty": bool(git("status", "--porcelain")),
        "branch": branch,
        "worktree": str(repo),
        "platform": platform.platform(),
        "python": platform.python_version(),
        "logical_cpus": os.cpu_count(),
        "python_executable": str(Path(sys.executable)).replace(
            str(Path.home()), "~", 1
        ),
        "command": subprocess.list2cmdline(command)
        if os.name == "nt"
        else shlex.join(command),
        "argv": command,
        "source_hashes": {
            str(p.relative_to(repo)): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(RUNTIME.rglob("*.py"))
        },
        "execution": "failed",
    }
    if args.events < 1_000_000:
        report["dataset"] = {"requested_events": args.events}
    started = time.perf_counter()
    home = Path(tempfile.mkdtemp(prefix="perf-home-", dir=output)).resolve()
    report["synthetic_home"] = str(home) if args.keep_home else "removed after run"
    try:
        if args.renderer_home is not None:
            shutil.copytree(
                args.renderer_home.resolve() / "browsers", home / "browsers"
            )
        report["dataset"] = seed(home, args.events, args.seed_seconds)
        exercise(home, args.samples, report, artifacts)
        report["execution"] = "completed"
    except (
        AssertionError,
        RuntimeError,
        ValueError,
        OSError,
        subprocess.SubprocessError,
    ) as error:
        # Do not serialize credentials, HTTP headers, process output or locals.
        report["error"] = (
            f"{type(error).__name__}: {error}"
            if isinstance(error, (AssertionError, RuntimeError, ValueError))
            else type(error).__name__
        )
    finally:
        report["seconds"] = time.perf_counter() - started
        if not args.keep_home:
            shutil.rmtree(home)
        raw = write_report(report, output, stem)
    print(
        json.dumps(
            {
                "report": str(raw),
                "execution": report["execution"],
                "events": report.get("dataset", {}).get("events"),
                "seconds": report["seconds"],
            }
        )
    )
    if args.events < 1_000_000:
        print(report["reference_scale_note"])
    return 0 if report["execution"] == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
