"""Native AC-33/45/51/62 evidence: real serve CLI, stores and optional Chromium.

Run with python3 -B sbtd-runtime/tests/runtime_e2e.py --output <directory>
--install-browser authorizes the pinned Playwright --only-shell download into
this run's disposable runtime home. No user runtime or browser profile is used.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import os
import platform
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import traceback
import unittest
import uuid
from datetime import UTC, datetime
from pathlib import Path

RUNTIME = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RUNTIME))

from browser_renderer import _prepare_document, _shell_executable
from export_render import default_presentation, load_panel_manifest
from runtime_e2e_diagnostics import diagnose
from test_csv_export import _dataset, _scope
from test_export_reconciliation import (
    ExportReconciliationTests,
    assert_key_values,
    assert_panels,
    assert_pdf_text,
)
from test_serve import (
    ServeProcess,
    _enable_observation,
    _free_port,
    _seed_golden_events,
    request,
)
from test_serve_signals import BreakShutdownTests


def _safe_text(text: str, secrets: list[str], limit: int | None = None) -> str:
    # Redact before slicing: a cap must never leave a credential prefix behind.
    values = {
        value
        for secret in secrets
        if secret
        for value in (secret, json.dumps(secret)[1:-1])
    }
    for value in sorted(values, key=len, reverse=True):
        text = text.replace(value, "<REDACTED>")
    assert not any(value in text for value in values), "evidence redaction failed"
    return text if limit is None else text[:limit]


def _capture_logs(
    home: Path, out: str, err: str, secrets: list[str], evidence: dict
) -> None:
    limit = 16_384
    logs = {
        "stdout": _safe_text(out, secrets, limit),
        "stderr": _safe_text(err, secrets, limit),
        "stdout_truncated": len(out) > limit,
        "stderr_truncated": len(err) > limit,
        "runtime_home_logs": [],
    }
    evidence["serve_logs"] = logs
    leaked = any(secret in out + err for secret in secrets if secret)
    ticket_url = "#ticket=" in out + err
    remaining = 65_536
    for path in sorted(home.rglob("*")):
        relative = path.relative_to(home)
        if not (".log" in path.name or "logs" in relative.parts):
            continue
        if not path.is_file() or path.is_symlink():
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        leaked |= any(secret in text for secret in secrets if secret)
        ticket_url |= "#ticket=" in text
        if remaining and len(logs["runtime_home_logs"]) < 32:
            cap = min(limit, remaining)
            safe = _safe_text(text, secrets, cap)
            logs["runtime_home_logs"].append(
                {
                    "path": _safe_text(str(relative), secrets, 512),
                    "text": safe,
                    "truncated": len(text) > cap,
                }
            )
            remaining -= len(safe)
        else:
            logs["runtime_home_logs_truncated"] = True
    # Keep the original security gate: sanitized evidence is not permission to leak.
    assert not leaked, "credential leaked"
    assert not ticket_url, "pairing URL leaked"


def verified_cjk_families(fonts: list[dict], *, required: bool = True) -> list[str]:
    cjk = [
        font["familyName"]
        for font in fonts
        if font["glyphCount"] > 0
        and any(
            marker in font["familyName"].lower()
            for marker in ("cjk", "pingfang", "hiragino", "yahei", "simsun", "unicode")
        )
    ]
    if required:
        assert cjk, "no verified CJK font produced heading glyphs"
    return cjk


def assert_font_records(records: dict, panels: list[str]) -> None:
    for name, record in records.items():
        assert record["fonts_ready"] == "loaded", "font readiness failed"
        assert record["panels"] == panels, "browser panel structure differs"
        assert record["cjk_text_present"], "CJK text missing"
        record["cjk_families"] = verified_cjk_families(
            record["platform_fonts"]["fonts"], required=name != "html"
        )
        record["status"] = "passed"


def browser_font_check(
    home: Path, documents: dict[str, str], panels: list[str], evidence: dict
) -> None:
    from playwright.sync_api import sync_playwright

    records = {}
    evidence["fonts"] = records
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=str(_shell_executable(home))
        )
        try:
            context = browser.new_context(service_workers="block")
            context.route("**/*", lambda route: route.abort())
            page = context.new_page()
            session = context.new_cdp_session(page)
            session.send("DOM.enable")
            session.send("CSS.enable")
            for name, document in documents.items():
                record = {
                    "status": "collecting",
                    "assertion": "仅记录、不断言" if name == "html" else "asserted",
                    "source": (
                        "downloaded HTML"
                        if name == "html"
                        else f"controlled renderer _prepare_document: {name}"
                    )
                    + "; real Chromium; not pixel OCR",
                    "evidence_source": "ci"
                    if os.environ.get("CI")
                    else "developer-local",
                    "platform": platform.platform(),
                }
                records[name] = record
                page.set_content(document)
                state = page.evaluate("""async () => {
                    await document.fonts.ready;
                    return {fonts: document.fonts.status,
                        panels: [...document.querySelectorAll('section.panel')].map(p => p.id),
                        text: document.body.innerText};
                }""")
                record.update(
                    fonts_ready=state["fonts"],
                    panels=state["panels"],
                    cjk_text_present="概览" in state["text"]
                    and "数据质量" in state["text"],
                )
                dom = session.send("DOM.getDocument")
                node = session.send(
                    "DOM.querySelector",
                    {"nodeId": dom["root"]["nodeId"], "selector": "#overview h2"},
                )
                # Preserve the complete CDP response before any gate can fail.
                record["platform_fonts"] = session.send(
                    "CSS.getPlatformFontsForNode", {"nodeId": node["nodeId"]}
                )
                record["status"] = "recorded"
            # Collect every document first, including PDF if JPEG's gate fails.
            assert_font_records(records, panels)
        finally:
            browser.close()


def exercise(
    home: Path, evidence: dict, install_browser: bool, secrets: list[str]
) -> None:
    case = unittest.TestCase()
    _enable_observation(home)
    _seed_golden_events(home)
    if install_browser:
        command = [
            sys.executable,
            "-m",
            "playwright",
            "install",
            "--only-shell",
            "chromium",
        ]
        installed = subprocess.run(
            command,
            env={**os.environ, "PLAYWRIGHT_BROWSERS_PATH": str(home / "browsers")},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
            timeout=300,
        )
        evidence["browser_install"] = {
            "command": command,
            "exit_code": installed.returncode,
            "stdout": installed.stdout,
            "stderr": installed.stderr,
        }
        case.assertEqual(
            installed.returncode,
            0,
            "pinned headless-shell installation failed; see browser_install evidence",
        )
    elif os.environ.get("SBTD_RENDERER_TEST_HOME"):
        shutil.copytree(
            Path(os.environ["SBTD_RENDERER_TEST_HOME"]) / "browsers", home / "browsers"
        )
        evidence["browser_install"] = {
            "source": "copy of explicit SBTD_RENDERER_TEST_HOME/browsers; no profile reused"
        }
    else:
        evidence["browser_install"] = {
            "source": "not requested; capability must describe unavailable renderer"
        }

    port = 6400
    with socket.socket() as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            port = _free_port()
    evidence["port"] = port
    evidence["default_port"] = port == 6400
    evidence["requests"] = []
    headers = {}

    def api(method, path, expected=200, body=None):
        status, response_headers, payload = request(
            port, method, path, body=body, headers=headers, host=f"localhost:{port}"
        )
        row = {"method": method, "path": path, "expected": expected, "status": status}
        evidence["requests"].append(row)
        if path == "/api/v1/session/pair":
            # Register issued credentials even if the response status is unexpected.
            csrf = {key.lower(): value for key, value in response_headers.items()}.get(
                "x-csrf-token"
            )
            if csrf:
                secrets.append(csrf)
            try:
                session = json.loads(payload)
            except (ValueError, UnicodeError):
                session = {}
            if isinstance(session, dict) and isinstance(
                session.get("access_token"), str
            ):
                secrets.append(session["access_token"])
        if status != expected:
            row["response_body"] = _safe_text(
                payload.decode("utf-8", errors="replace"), secrets, 4096
            )
            row["response_body_truncated"] = len(payload) > 4096
        case.assertEqual(status, expected, f"{method} {path}")
        return response_headers, payload

    server = ServeProcess(home, port, "--no-open")
    out = err = ""
    try:
        server.wait_ready()
        _, health = api("GET", "/api/v1/health")
        case.assertEqual(json.loads(health), {"status": "ok"})
        _, dashboard = api("GET", "/")
        case.assertIn(b"<html", dashboard.lower())
        ticket_file = home / "pairing-ticket"
        mode = ticket_file.stat().st_mode & 0o777
        if os.name != "nt":
            case.assertEqual(mode, 0o600)
        evidence["ticket_file"] = {
            "mode": oct(mode),
            "permission_evidence": "POSIX 0600 asserted"
            if os.name != "nt"
            else "Windows chmod is not a POSIX ACL proof; isolated runner temp home",
        }
        ticket = ticket_file.read_text(encoding="utf-8").strip()
        secrets.append(ticket)
        headers["X-Pairing-Code"] = ticket
        pair_headers, pair_body = api("POST", "/api/v1/session/pair")
        session = json.loads(pair_body)
        pair_headers = {key.lower(): value for key, value in pair_headers.items()}
        headers.update(
            {
                "Authorization": f"Bearer {session['access_token']}",
                "X-CSRF-Token": pair_headers["x-csrf-token"],
            }
        )
        api("POST", "/api/v1/session/pair", 401)
        headers.pop("X-Pairing-Code")
        _, catalog_bytes = api("GET", "/api/v1/metrics/catalog")
        catalog = json.loads(catalog_bytes)["data"]
        manifest = load_panel_manifest()
        presentation = default_presentation(manifest)
        metrics = sorted(
            {metric for panel in manifest["panels"] for metric in panel["metric_ids"]}
        )
        case.assertTrue(
            set(metrics) <= {metric["metric_id"] for metric in catalog["metrics"]}
        )
        _, query_bytes = api(
            "POST", "/api/v1/statistics/query", body=_scope(_dataset(), metrics)
        )
        answer = json.loads(query_bytes)["data"]
        snapshot_id = answer["snapshot_id"]
        # API ingestion derives tasks from events (no summary role field); use
        # this snapshot's API values, not the richer library fixture's task table.
        expected_values = {
            metric: str(answer["metrics"][metric]["value"])
            for metric in ("tasks.touched", "steps.success_rate_observed")
        }
        _, capabilities = api("GET", "/api/v1/capabilities")
        formats = json.loads(capabilities)["data"]["exports"]
        evidence["capabilities"] = formats
        payloads = {}
        evidence["exports"] = {}
        for format_name in ("html", "csv", "jpeg", "pdf"):
            headers["Idempotency-Key"] = uuid.uuid4().hex
            body = {"snapshot_id": snapshot_id, "format": format_name}
            if not formats[format_name]["available"]:
                case.assertIn(format_name, ("jpeg", "pdf"))
                case.assertTrue(formats[format_name]["reason"])
                case.assertFalse(formats[format_name]["http_available"])
                _, rejected = api("POST", "/api/v1/exports", 503, body)
                case.assertEqual(
                    json.loads(rejected), {"detail": "EXPORT_RENDERER_UNAVAILABLE"}
                )
                evidence["exports"][format_name] = {
                    "status": "unavailable",
                    "reason": formats[format_name]["reason"],
                }
                continue
            export_id = None
            try:
                _, accepted = api("POST", "/api/v1/exports", 202, body)
                export_id = json.loads(accepted)["data"]["export_id"]
                deadline = time.monotonic() + 90
                while True:
                    _, state = api("GET", f"/api/v1/exports/{export_id}")
                    info = json.loads(state)["data"]
                    if info["status"] == "ready":
                        break
                    case.assertIn(info["status"], ("queued", "generating"))
                    case.assertLess(time.monotonic(), deadline, "export timeout")
                    time.sleep(0.2)
            except Exception:  # Diagnose, then preserve the original failure.
                if format_name in ("jpeg", "pdf"):
                    evidence["renderer_diagnostics"] = diagnose(
                        home,
                        payloads["html"],
                        format_name,
                        preflight=format_name == "jpeg" and export_id is None,
                        sanitize=lambda text: _safe_text(text, secrets),
                    )
                raise
            download_headers, payload = api("GET", f"/api/v1/exports/{export_id}/file")
            case.assertEqual(info["snapshot_id"], snapshot_id)
            case.assertEqual(info["sha256"], hashlib.sha256(payload).hexdigest())
            case.assertEqual(info["byte_size"], len(payload))
            case.assertIn(format_name, download_headers.get("content-type", ""))
            if format_name == "jpeg":
                case.assertTrue(payload.startswith(b"\xff\xd8\xff"))
            if format_name == "pdf":
                case.assertTrue(payload.startswith(b"%PDF-"))
            payloads[format_name] = payload
            evidence["exports"][format_name] = {
                "status": "passed",
                "sha256": info["sha256"],
                "byte_size": len(payload),
            }
        documents = {"html": payloads["html"].decode("utf-8")}
        evidence["key_values"] = assert_key_values(
            case, documents, payloads["csv"], expected_values
        )
        evidence["panels"] = assert_panels(case, documents, payloads["csv"])
        if "pdf" in payloads:
            evidence["pdf_text"] = assert_pdf_text(
                case, payloads["pdf"], evidence["panels"], expected_values
            )
        if "jpeg" in payloads or "pdf" in payloads:
            font_documents = {
                "html": documents["html"],
                **{
                    name: _prepare_document(documents["html"], name, presentation)
                    for name in ("jpeg", "pdf")
                    if name in payloads
                },
            }
            browser_font_check(home, font_documents, evidence["panels"], evidence)
        else:
            evidence["fonts"] = {
                "status": "unavailable",
                "reason": formats["jpeg"]["reason"],
            }
        # Same source-document boundary tests as the local runtime suite, using
        # the real installed browser on capable native runners (no stub there).
        previous_home = os.environ.get("SBTD_RENDERER_TEST_HOME")
        os.environ["SBTD_RENDERER_TEST_HOME"] = str(home)
        try:
            stream = io.StringIO()
            suite = unittest.TestSuite(
                unittest.defaultTestLoader.loadTestsFromTestCase(kind)
                for kind in (ExportReconciliationTests, BreakShutdownTests)
            )
            result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
            evidence["reconciliation"] = {
                "tests": result.testsRun,
                "failures": len(result.failures),
                "errors": len(result.errors),
                "skipped": len(result.skipped),
                "output": stream.getvalue(),
                "renderer": "real"
                if formats["jpeg"]["available"]
                else "existing worker stub",
            }
            case.assertTrue(
                result.wasSuccessful(),
                "reconciliation or break-shutdown regression failed",
            )
            case.assertEqual(result.skipped, [])
        finally:
            if previous_home is None:
                os.environ.pop("SBTD_RENDERER_TEST_HOME", None)
            else:
                os.environ["SBTD_RENDERER_TEST_HOME"] = previous_home
    finally:
        try:
            out, err, code = (
                server.stop()
                if server.proc.poll() is None
                else (*server.proc.communicate(), server.proc.returncode)
            )
        finally:
            if server.proc.poll() is None:
                out, err = server.kill()
            # Startup can fail before the normal ticket read. Never persist it.
            ticket_path = home / "pairing-ticket"
            if ticket_path.is_file():
                secrets.append(ticket_path.read_text(encoding="utf-8").strip())
            _capture_logs(home, out, err, secrets, evidence)
        evidence["shutdown"] = {
            "exit_code": code,
            "signal": "CTRL_BREAK_EVENT" if os.name == "nt" else "SIGINT",
            "lock_removed": not (home / "serve.lock").exists(),
        }
        case.assertEqual(code, 0, "serve did not exit cleanly")
        case.assertFalse((home / "serve.lock").exists())
        case.assertFalse(any((home / "exports").glob("*.tmp")))
        with socket.socket() as probe:
            case.assertNotEqual(
                probe.connect_ex(("127.0.0.1", port)), 0, "server still listening"
            )
        evidence["shutdown"]["port_closed"] = True


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--install-browser", action="store_true")
    args = parser.parse_args()
    started = datetime.now(UTC)
    clock = time.monotonic()
    sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=RUNTIME.parent, text=True
    ).strip()
    branch = (
        os.environ.get("GITHUB_HEAD_REF")
        or subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=RUNTIME.parent, text=True
        ).strip()
    )
    dirty = bool(
        subprocess.check_output(
            ["git", "status", "--porcelain"], cwd=RUNTIME.parent, text=True
        ).strip()
    )
    evidence = {
        "started_at": started.isoformat(),
        "platform": platform.platform(),
        "python": sys.version,
        "sha": sha,
        "branch": branch,
        "worktree": str(RUNTIME.parent),
        "source_revision": "dirty" if dirty else "exact",
        "evidence_source": "ci" if os.environ.get("CI") else "developer-local",
        "publication": "not-configured" if os.environ.get("CI") else "local-only",
        "command": sys.argv,
        "serve_logs": {
            "stdout": "",
            "stderr": "",
            "runtime_home_logs": [],
            "capture": "serve not started",
        },
        "limitations": [
            "Mac visual/font confirmation pending; Windows CI only",
            "JPEG source-document values; pixel OCR not performed",
            "PDF text verified only when pdftotext produces usable UTF-8 text",
            "Performance section 18 belongs to PR-4",
            "Windows chmod is not POSIX 0600 ACL evidence",
        ],
    }
    code = 1
    secrets: list[str] = []
    try:
        with tempfile.TemporaryDirectory(prefix="sbtd-native-e2e-") as temporary:
            home = Path(temporary).resolve()
            exercise(home, evidence, args.install_browser, secrets)
        evidence["temporary_home_removed"] = not home.exists()
        evidence["status"] = (
            "passed"
            if all(row["status"] == "passed" for row in evidence["exports"].values())
            else "passed-with-renderer-unavailable"
        )
        code = 0
    except Exception as error:  # noqa: BLE001 — report failures; never convert them to PASS.
        evidence["status"] = "failed"
        evidence["error"] = f"{type(error).__name__}: {error}"
        evidence["traceback"] = traceback.format_exc()
    evidence["exit_code"] = code
    evidence["seconds"] = round(time.monotonic() - clock, 3)
    # Also sanitize exception/traceback and embedded test output before either file.
    evidence = json.loads(_safe_text(json.dumps(evidence, ensure_ascii=False), secrets))
    args.output.mkdir(parents=True, exist_ok=True)
    slug = branch.replace("/", "_")
    stem = f"runtime-e2e-{platform.system().lower()}-{slug}-{started.strftime('%Y%m%dT%H%M%SZ')}"
    raw = args.output / f"{stem}.json"
    raw.write_text(
        json.dumps(evidence, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    sections = [
        (
            "执行结论",
            f"结果：{evidence['status']}；退出码 {code}；耗时 {evidence['seconds']} 秒。renderer unavailable 不是四格式通过。",
        ),
        (
            "运行信息",
            f"{started.isoformat()}；{evidence['platform']}；Python {platform.python_version()}；分支 {branch}；SHA {sha}；{evidence['source_revision']}；{evidence['evidence_source']}；{evidence['publication']}；E2E Mode backend-only + real renderer（可用时）；rtk skipped-for-report。",
        ),
        ("运行命令", "```text\n" + " ".join(sys.argv) + "\n```"),
        (
            "关联 BDD 与本轮范围",
            "AC-33/62：真实 serve CLI、配对、API、退出；AC-45/51：HTML/CSV、renderer 输入、可用时 PDF 文本。沿用 R2.0a／R2.1a／R2.1b Markdown 规范。",
        ),
        (
            "用例结果",
            "| 格式 | 结果 | 原因 |\n|---|---|---|\n"
            + "\n".join(
                f"| {name} | {row['status']} | {row.get('reason', '—')} |"
                for name, row in evidence.get("exports", {}).items()
            ),
        ),
        (
            "失败、修复与复跑",
            evidence.get(
                "error",
                "本轮无失败；历史轮次不覆盖。能力不可用见上表，不计作渲染通过。",
            )
            + (
                "\n\n```text\n" + evidence["traceback"] + "```"
                if "traceback" in evidence
                else ""
            )
            + (
                "\n\n```json\n"
                + json.dumps(
                    evidence["renderer_diagnostics"], ensure_ascii=False, indent=2
                )
                + "\n```"
                if "renderer_diagnostics" in evidence
                else ""
            ),
        ),
        (
            "覆盖范围 → API URI",
            "| Method | URI | 期望 | 实际 |\n|---|---|---|---|\n"
            + "\n".join(
                f"| {row['method']} | {row['path']} | {row['expected']} | {row['status']} |"
                for row in evidence.get("requests", [])
            ),
        ),
        (
            "产物与状态",
            f"原生 raw：{raw.name}；同 stem 中文汇总。报告生成不等于测试通过；未发布。",
        ),
        (
            "未执行项、风险与发布边界",
            "\n".join(f"- {item}" for item in evidence["limitations"])
            + "\n- 跨平台结果仅由各自原生 runner 证明；本地 Linux 不替代 CI。",
        ),
    ]
    raw.with_suffix(".md").write_text(
        "# 原生 Runtime E2E 报告\n\n"
        + "\n\n".join(f"## {title}\n\n{body}" for title, body in sections)
        + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": evidence["status"],
                "report": str(raw),
                "seconds": evidence["seconds"],
            }
        )
    )
    return code


if __name__ == "__main__":
    raise SystemExit(main())
