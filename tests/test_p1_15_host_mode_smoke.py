from __future__ import annotations

import os
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


def _words_and_bytes(path: Path) -> tuple[int, int]:
    text = path.read_text(encoding="utf-8")
    return len(text.encode("utf-8")), len(text.split())


def _config_digest() -> tuple[tuple[str, int, int], ...]:
    rows = []
    home = Path.home()
    for relative in (
        ".codex/config.toml",
        ".omp/agent/mcp.json",
        ".omp/agent/AGENTS.md",
    ):
        path = home / relative
        if not path.is_file():
            continue
        stat = path.stat()
        rows.append((relative, stat.st_size, int(stat.st_mtime)))
    return tuple(rows)


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
                results.append(
                    {"host": host, "status": "blocked", "reason": "cli-missing"}
                )
                continue
            for mode in MODES:
                results.append(self._run_host_mode(host, binary, mode))
        blocked = [item for item in results if item["status"] == "blocked"]
        failed = [item for item in results if item["status"] == "failed"]
        self.assertFalse(failed, failed)
        self.assertEqual(len(results), 6, results)
        if blocked:
            self.fail(f"host sessions blocked, not passing AC-04: {blocked!r}")

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
            prompt = (
                f"SBTD execution mode is {mode}. Read AGENTS.md and MODE. "
                "Reply with one JSON object "
                f'{{"mode":"{mode}","writes":false}} '
                "and do not create or edit files."
            )
            home_before = _config_digest()
            completed = self._invoke(host, binary, root, project, prompt)
            extra = [
                path.relative_to(project).as_posix()
                for path in project.rglob("*")
                if path.is_file()
                and not str(path.relative_to(project)).startswith(".git/")
                and path.name not in {"AGENTS.md", "MODE"}
            ]
            payload: dict[str, object] = {
                "host": host,
                "mode": mode,
                "returncode": completed.returncode,
                "stdout": (completed.stdout or "")[-4000:],
                "stderr": (completed.stderr or "")[-2000:],
            }
            if completed.returncode != 0:
                payload["status"] = "failed"
                payload["reason"] = "nonzero-exit"
                return payload
            if extra:
                payload["status"] = "failed"
                payload["reason"] = f"unexpected-writes:{extra}"
                return payload
            if home_before != _config_digest():
                payload["status"] = "failed"
                payload["reason"] = "home-changed"
                return payload
            combined = ((completed.stdout or "") + (completed.stderr or "")).lower()
            if mode not in combined:
                payload["status"] = "failed"
                payload["reason"] = "mode-not-observed"
                return payload
            payload["status"] = "passed"
            return payload
        finally:
            temporary.cleanup()

    def _invoke(
        self,
        host: str,
        binary: str,
        isolation: Path,
        project: Path,
        prompt: str,
    ) -> subprocess.CompletedProcess[str]:
        env = os.environ.copy()
        env["PI_CODING_AGENT_DIR"] = str(isolation / "omp-agent")
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
                prompt,
            ]
        else:
            command = [
                binary,
                "--print",
                "--no-session",
                "--profile",
                "p115-smoke",
                "--cwd",
                str(project),
                "--no-extensions",
                "--approval-mode",
                "always-ask",
                prompt,
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
