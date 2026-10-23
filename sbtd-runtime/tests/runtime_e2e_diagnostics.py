"""Failure-only native E2E probes; production worker behaviour stays unchanged."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
import traceback
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import browser_renderer as renderer

LIMIT = 16_384


def _exception_chain(error: BaseException) -> list[dict]:
    chain = []
    seen = set()
    while error is not None and id(error) not in seen:
        seen.add(id(error))
        frames = traceback.extract_tb(error.__traceback__)
        chain.append(
            {
                "type": type(error).__name__,
                "site": (
                    f"{frames[-1].filename}:{frames[-1].lineno}:{frames[-1].name}"
                    if frames
                    else "no traceback"
                ),
                "traceback": "".join(
                    traceback.format_exception(
                        type(error), error, error.__traceback__, chain=False
                    )
                ),
                "next": "cause" if error.__cause__ is not None else "context",
            }
        )
        # Renderer deliberately suppresses public exception context. The test-only
        # probe retains it, including `raise ... from None`, for local diagnosis.
        error = error.__cause__ if error.__cause__ is not None else error.__context__
    return chain


def _worker_argv(job: Path) -> list[str]:
    return [sys.executable, "-B", str(Path(__file__).resolve()), "--worker", str(job)]


def worker_main(job_dir: str) -> int:
    write_error = renderer._write_error

    def record_error(job, error):
        write_error(job, error)
        chain = _exception_chain(sys.exception() or error)
        (job / "exception.json").write_text(json.dumps(chain), encoding="utf-8")

    with patch.object(renderer, "_write_error", side_effect=record_error):
        return renderer._worker_entry(job_dir)


def diagnose(
    home: Path, document: bytes, format_name: str, *, preflight: bool, sanitize
) -> dict:
    """Replay the same snapshot HTML through job write, worker, wait and cleanup.

    No Store is opened or modified. This is a separate diagnostic attempt, not
    evidence that the original export succeeded. Only stdio/exception capture
    differs; production deadlines, process ownership and result validation run.
    """
    evidence = {
        "source": "test-side replay of downloaded HTML from the failed export snapshot",
        "document_sha256": hashlib.sha256(document).hexdigest(),
        "format": format_name,
        "preflight": preflight,
        "workers": [],
    }
    execute = renderer._execute_job
    popen = subprocess.Popen

    def capped(text):
        safe = sanitize(text)
        return {"content": safe[:LIMIT], "truncated": len(safe) > LIMIT}

    def capture(job, profile, cancelled, deadline):
        worker = {"exit_code": None, "files": {}}
        evidence["workers"].append(worker)
        processes = []
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:

            def spawn(*args, **kwargs):
                kwargs.update(stdout=stdout, stderr=stderr)
                proc = popen(*args, **kwargs)
                processes.append(proc)
                return proc

            try:
                with patch.object(renderer.subprocess, "Popen", side_effect=spawn):
                    return execute(job, profile, cancelled, deadline)
            finally:
                if processes:
                    worker["exit_code"] = processes[0].returncode
                for name, stream in (("stdout", stdout), ("stderr", stderr)):
                    stream.seek(0)
                    worker[name] = capped(
                        stream.read().decode("utf-8", errors="replace")
                    )
                for name in ("error.json", "result.json", "exception.json"):
                    path = job / name
                    exists = path.is_file()
                    worker["files"][name] = {"exists": exists}
                    if exists:
                        worker["files"][name].update(
                            capped(path.read_text(encoding="utf-8", errors="replace"))
                        )

    try:
        with (
            patch.object(renderer, "_execute_job", side_effect=capture),
            patch.object(renderer, "_worker_argv", side_effect=_worker_argv),
        ):
            renderer._render_document(
                document,
                format_name,
                home=home,
                cancelled=None,
                presentation=None,
                preflight=preflight,
            )
        evidence["status"] = "diagnostic-replay-succeeded; original export still failed"
    except Exception as error:  # noqa: BLE001 — diagnosis never replaces the original failure.
        evidence["status"] = "failed"
        evidence["exception_chain"] = [
            {key: capped(value)["content"] for key, value in row.items()}
            for row in _exception_chain(error)
        ]
    return evidence


if __name__ == "__main__":
    if len(sys.argv) != 3 or sys.argv[1] != "--worker":
        raise SystemExit(2)
    raise SystemExit(worker_main(sys.argv[2]))
