from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GLOBAL_AGENTS = ROOT / "sbtd-workflow-onboard/templates/agents/AGENTS.global.md"
PROJECT_AGENTS = ROOT / "sbtd-workflow-onboard/templates/agents/AGENTS.project.md"
TASK_SKILL = ROOT / "sbtd-workflow-onboard/templates/skills/sbtd-task/SKILL.md"
STRICT_REF = ROOT / "sbtd-workflow-onboard/templates/skills/sbtd-task/references/strict.md"
HOST_OPT_IN = "SBTD_P115_HOST"
MODES = ("default", "lite", "strict")
HOSTS = ("codex", "omp")
HOST_PROMPT = (
    "Read workspace files AGENTS.md and MODE. "
    "Reply with one JSON object whose keys are mode and writes. "
    "Do not create or edit files."
)
_JSON_OBJECT = re.compile(r"\{[^{}]*\}")
_AUTH_MARKERS = (
    "not logged in",
    "please log in",
    "please login",
    "authentication",
    "unauthenticated",
    "missing api",
    "api key",
    "no api key",
    "401",
    "403",
    "auth required",
    "not authenticated",
)


def _words_and_bytes(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    return len(text.encode("utf-8")), len(text.split())


def _copy_codex_auth(destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    source = Path.home() / ".codex" / "auth.json"
    if source.is_file():
        shutil.copy2(source, destination / "auth.json")


def _extract_mode_report(text: str) -> dict[str, object] | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("{") and stripped.endswith("}"):
            try:
                parsed = json.loads(stripped)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict) and "mode" in parsed:
                return parsed
            inner = parsed.get("item") if isinstance(parsed, dict) else None
            if isinstance(inner, dict) and isinstance(inner.get("text"), str):
                nested = _extract_mode_report(inner["text"])
                if nested is not None:
                    return nested
    match = _JSON_OBJECT.findall(text)
    for blob in reversed(match):
        try:
            parsed = json.loads(blob)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict) and "mode" in parsed:
            return parsed
    return None


def _auth_blocked(stdout: str, stderr: str, returncode: int) -> bool:
    haystack = f"{stdout}\n{stderr}".lower()
    if any(marker in haystack for marker in _AUTH_MARKERS):
        return True
    return returncode != 0 and "login" in haystack


class HostModeSmokeTests(unittest.TestCase):
    def test_entry_file_sizes_are_observations_not_token_claims(self) -> None:
        public_core = (GLOBAL_AGENTS, TASK_SKILL)
        tracked = public_core + (STRICT_REF,)
        observations = {}
        for path in tracked:
            size, words = _words_and_bytes(path)
            observations[path.name] = {
                "bytes": size,
                "whitespaceWords": words,
                "tokens": None,
            }
        self.assertTrue(GLOBAL_AGENTS.is_file())
        self.assertTrue(TASK_SKILL.is_file())
        self.assertTrue(STRICT_REF.is_file())
        self.assertTrue(PROJECT_AGENTS.is_file())
        for item in observations.values():
            self.assertIsNone(item["tokens"])
            self.assertGreater(item["bytes"], 0)
        core_words = sum(
            observations[path.name]["whitespaceWords"] for path in public_core
        )
        self.assertGreater(core_words, 0)

    def test_host_prompt_does_not_name_a_mode(self) -> None:
        lowered = HOST_PROMPT.lower()
        for mode in MODES:
            self.assertNotIn(mode, lowered)

    def test_extract_mode_report_from_json_and_jsonl(self) -> None:
        self.assertEqual(
            _extract_mode_report('noise {"mode":"lite","writes":false} tail')["mode"],
            "lite",
        )
        jsonl = (
            '{"type":"thread.started"}\n'
            '{"item":{"text":"{\\"mode\\":\\"strict\\",\\"writes\\":false}"}}\n'
        )
        self.assertEqual(_extract_mode_report(jsonl)["mode"], "strict")

    def test_host_matrix_requires_explicit_opt_in(self) -> None:
        if os.environ.get(HOST_OPT_IN) == "1":
            self.skipTest("host opt-in is set; matrix runs in the live host test")
        self.assertNotEqual(os.environ.get(HOST_OPT_IN), "1")

    def test_live_host_mode_matrix(self) -> None:
        if os.environ.get(HOST_OPT_IN) != "1":
            self.skipTest(f"set {HOST_OPT_IN}=1 to run real Codex/OMP sessions")
        results = []
        for host in HOSTS:
            binary = shutil.which(host)
            if binary is None:
                for mode in MODES:
                    results.append(
                        {
                            "host": host,
                            "mode": mode,
                            "status": "blocked",
                            "reason": "cli-missing",
                        }
                    )
                continue
            for mode in MODES:
                results.append(self._run_host_mode(host, binary, mode))
        failed = [item for item in results if item["status"] == "failed"]
        self.assertFalse(failed, failed)
        self.assertEqual(len(results), 6, results)
        passed = [item for item in results if item["status"] == "passed"]
        if len(passed) != 6:
            self.skipTest(f"host matrix is not AC-04 pass: {results!r}")

    def _run_host_mode(self, host: str, binary: str, mode: str) -> dict[str, object]:
        temporary = tempfile.TemporaryDirectory(prefix=f"sbtd-p115-{host}-{mode}-")
        try:
            root = Path(temporary.name)
            project = root / "project"
            project.mkdir()
            subprocess.run(
                ["git", "init", "-b", "main", str(project)],
                check=True,
                capture_output=True,
            )
            (project / "AGENTS.md").write_text(
                f"当前任务执行模式: {mode}\n\n"
                + GLOBAL_AGENTS.read_text(encoding="utf-8")
                + "\n\n"
                + PROJECT_AGENTS.read_text(encoding="utf-8"),
                encoding="utf-8",
            )
            (project / "MODE").write_text(mode + "\n", encoding="utf-8")
            completed = self._invoke(host, binary, root, project)
            extra = [
                path.relative_to(project).as_posix()
                for path in project.rglob("*")
                if path.is_file()
                and not str(path.relative_to(project)).startswith(".git/")
                and path.name not in {"AGENTS.md", "MODE"}
            ]
            stdout = completed.stdout or ""
            stderr = completed.stderr or ""
            payload: dict[str, object] = {
                "host": host,
                "mode": mode,
                "returncode": completed.returncode,
                "stdout": stdout[-4000:],
                "stderr": stderr[-2000:],
            }
            if extra:
                payload["status"] = "failed"
                payload["reason"] = f"unexpected-project-writes:{extra}"
                return payload
            if _auth_blocked(stdout, stderr, completed.returncode):
                payload["status"] = "blocked"
                payload["reason"] = "auth"
                return payload
            if completed.returncode != 0:
                payload["status"] = "failed"
                payload["reason"] = "nonzero-exit"
                return payload
            report = _extract_mode_report(stdout)
            if report is None or report.get("mode") != mode:
                payload["status"] = "failed"
                payload["reason"] = f"mode-mismatch:{report}"
                return payload
            payload["status"] = "passed"
            payload["report"] = report
            return payload
        finally:
            temporary.cleanup()

    def _invoke(
        self,
        host: str,
        binary: str,
        isolation: Path,
        project: Path,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        home = isolation / "home"
        home.mkdir()
        env["HOME"] = str(home)
        env["USERPROFILE"] = str(home)
        env["PI_CODING_AGENT_DIR"] = str(home / ".omp" / "agent")
        env["CODEX_HOME"] = str(home / ".codex")
        _copy_codex_auth(Path(env["CODEX_HOME"]))
        if host == "codex":
            command = [
                binary,
                "exec",
                "--ephemeral",
                "--sandbox",
                "read-only",
                "--skip-git-repo-check",
                "--json",
                "-C",
                str(project),
                HOST_PROMPT,
            ]
        else:
            command = [
                binary,
                "--print",
                "--no-session",
                "--cwd",
                str(project),
                "--no-extensions",
                "--tools",
                "read",
                HOST_PROMPT,
            ]
        return subprocess.run(
            command,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=180,
            check=False,
        )


if __name__ == "__main__":
    unittest.main()
