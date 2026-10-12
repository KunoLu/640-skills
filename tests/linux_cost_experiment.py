"""Temporary paired Linux CI cost experiment runner; deleted after the proof.

Pair mode runs the real committed CI shard (tests/run_ci.py) once in the frozen
baseline checkout and once in the candidate checkout on the same runner, in the
round's order (1: baseline→candidate, 2: candidate→baseline, 3: baseline→candidate).
Coverage mode runs one checkout's real shard under coverage==7.16.2 for Main's
executed line/branch union comparison. Both modes preserve native return codes,
raw stdout/stderr, native JSON/inventories and same-stem Chinese summaries, and
assert the Onboard source did not drift. Raw measurements only: no savings or
performance claims are computed here; aggregation happens outside the workflow.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

BASE_SHA = "2aef801a93aece7a3999fff0bb577c695042948f"
SHARDS = 3
ROUND_ORDERS = {1: ("baseline", "candidate"), 2: ("candidate", "baseline"), 3: ("baseline", "candidate")}
ONBOARD = "sbtd-workflow-onboard"
MIN_TOMLKIT = "0.13.2"
ENV_WHITELIST = (
    "RUNNER_OS", "RUNNER_ARCH", "RUNNER_NAME", "ImageOS", "ImageVersion",
    "GITHUB_SHA", "GITHUB_REF", "GITHUB_RUN_ID", "GITHUB_RUN_NUMBER",
    "GITHUB_RUN_ATTEMPT", "GITHUB_WORKFLOW", "GITHUB_JOB",
)


def utcnow():
    return datetime.now(timezone.utc).isoformat()


def run_logged(argv, cwd, env, stem):
    """Run one command, teeing raw stdout/stderr to files and the Actions log."""
    tick = time.monotonic()
    note = ""
    with open(f"{stem}.stdout.log", "wb") as out, open(f"{stem}.stderr.log", "wb") as err:
        try:
            proc = subprocess.Popen(argv, cwd=cwd, env=env,
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        except OSError as exc:
            err.write(f"failed to start: {exc}\n".encode())
            return 127, time.monotonic() - tick, str(exc)

        def pump(source, *sinks):
            while True:
                chunk = source.read(65536)
                if not chunk:
                    break
                for sink in sinks:
                    sink.write(chunk)
                    sink.flush()

        threads = [
            threading.Thread(target=pump, args=(proc.stdout, out, sys.stdout.buffer), daemon=True),
            threading.Thread(target=pump, args=(proc.stderr, err, sys.stderr.buffer), daemon=True),
        ]
        for thread in threads:
            thread.start()
        returncode = proc.wait()
        for thread in threads:
            thread.join()
    return returncode, time.monotonic() - tick, note


class Recorder:
    """Boring per-run command journal; raw streams land in commands/ files."""

    def __init__(self, root, cwd, env, timed):
        self.root = Path(root)
        self.cwd = str(cwd)
        self.env = env
        self.timed = timed
        self.commands = []
        (self.root / "commands").mkdir(parents=True, exist_ok=True)

    def execute(self, name, argv, ci_core=False, extra_env=None):
        stem = self.root / "commands" / f"{len(self.commands) + 1:02d}-{name}"
        env = {**self.env, **(extra_env or {})}
        returncode, elapsed, note = run_logged([str(arg) for arg in argv], self.cwd, env, stem)
        record = {
            "name": name, "argv": [str(arg) for arg in argv], "cwd": self.cwd,
            "returncode": returncode,
            "stdout_log": f"commands/{stem.name}.stdout.log",
            "stderr_log": f"commands/{stem.name}.stderr.log",
        }
        if self.timed:
            record["elapsed_seconds"] = round(elapsed, 3)
            record["ci_core"] = ci_core
        if note:
            record["note"] = note
        self.commands.append(record)
        timing = f" elapsed={elapsed:.3f}s" if self.timed else ""
        print(f"[{Path(self.cwd).name}] {name}: rc={returncode}{timing}", flush=True)
        return record

    def text(self, record):
        return (self.root / record["stdout_log"]).read_text(encoding="utf-8").strip()


def snapshot_source(root):
    """Hash every Onboard entry, including empty directories and generated pyc."""
    entries = {}
    for path in sorted(Path(root).rglob("*")):
        rel = path.relative_to(root).as_posix()
        if path.is_symlink():
            entries[rel] = {"type": "symlink", "target": os.readlink(path)}
        elif path.is_dir():
            entries[rel] = {"type": "directory"}
        elif path.is_file():
            entries[rel] = {"type": "file", "sha256": hashlib.sha256(path.read_bytes()).hexdigest()}
        else:
            raise RuntimeError(f"Unsupported source entry: {rel}")
    return entries


def drift_differences(pre, post):
    differences = []
    for rel in sorted(set(pre) | set(post)):
        if rel not in pre:
            differences.append(f"added: {rel}")
        elif rel not in post:
            differences.append(f"removed: {rel}")
        elif pre[rel] != post[rel]:
            differences.append(f"changed: {rel}")
    return differences


def capture_metadata(output_dir):
    """Whitelisted environment/dependency/image metadata; never a full env dump."""
    metadata_dir = Path(output_dir) / "metadata"
    metadata_dir.mkdir(parents=True, exist_ok=True)
    freeze = subprocess.run(
        [sys.executable, "-m", "pip", "freeze"], capture_output=True, text=True, check=False
    )
    (metadata_dir / "pip-freeze.txt").write_text(freeze.stdout, encoding="utf-8")
    if freeze.returncode != 0:
        (metadata_dir / "pip-freeze.stderr.txt").write_text(freeze.stderr, encoding="utf-8")
        raise SystemExit("pip freeze failed; cannot prove dependency metadata")
    declared = ""
    for line in freeze.stdout.splitlines():
        if line.startswith("tomlkit=="):
            declared = line.split("==", 1)[1].strip()
    return {
        "python": sys.version,
        "platform": platform.platform(),
        "umask": "0o022",
        "environment": {key: os.environ[key] for key in ENV_WHITELIST if key in os.environ},
        "dependencies_file": "metadata/pip-freeze.txt",
        "dependencies": freeze.stdout.splitlines(),
        "tomlkit_declared": declared,
    }


def finish_variant(journal, variant_dir, sha, tree, started_at, tick, pre, extra):
    """Shared variant tail: post snapshot, drift assert, cleanliness, verdict."""
    snapshots_dir = Path(variant_dir) / "snapshots"
    post = snapshot_source(Path(journal.cwd) / ONBOARD)
    (snapshots_dir / "onboard-post.json").write_text(json.dumps(post, indent=2), encoding="utf-8")
    differences = drift_differences(pre, post)
    clean = journal.text(journal.execute("git-status", ["git", "status", "--porcelain"])) == ""
    failed = [command["name"] for command in journal.commands if command["returncode"] != 0]
    record = {
        "checkout": journal.cwd,
        "git_sha": sha,
        "production_tree": tree,
        "started_at": started_at,
        "finished_at": utcnow(),
        "commands": journal.commands,
        "drift": {
            "checked_files": len(pre),
            "equal": not differences,
            "differences": differences,
            "pre_snapshot": "snapshots/onboard-pre.json",
            "post_snapshot": "snapshots/onboard-post.json",
        },
        "checkout_clean": clean,
        "results_dir": "results",
        "failed_commands": failed,
        "successful": not failed and not differences and clean,
    }
    record.update(extra)
    if tick is not None:
        record["variant_elapsed_seconds"] = round(time.monotonic() - tick, 3)
        record["ci_core_seconds"] = round(
            sum(command["elapsed_seconds"] for command in journal.commands if command.get("ci_core")), 3)
        record["ci_core_excludes"] = ["tomlkit-restore", "git metadata", "source snapshots"]
    return record


def run_ci_variant(label, checkout, shard, variant_dir, declared_tomlkit):
    """Mirror the real CI job in one checkout: compileall, shard gates, native run_ci."""
    checkout = Path(checkout)
    variant_dir = Path(variant_dir)
    results_dir = variant_dir / "results"
    snapshots_dir = variant_dir / "snapshots"
    for directory in (results_dir, snapshots_dir):
        directory.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    journal = Recorder(variant_dir, checkout, env, timed=True)
    started_at = utcnow()
    tick = time.monotonic()
    sha = journal.text(journal.execute("git-sha", ["git", "rev-parse", "HEAD"]))
    env["VALIDATION_SHA"] = sha
    tree = journal.text(journal.execute("git-tree", ["git", "rev-parse", f"HEAD:{ONBOARD}"]))
    journal.execute("compileall", [sys.executable, "-m", "compileall", "-q", f"{ONBOARD}/scripts", "tests"],
                    ci_core=True)
    if shard == 1:
        journal.execute("bash-syntax", ["bash", "-n", "install.sh"], ci_core=True)
    pre = snapshot_source(checkout / ONBOARD)
    (snapshots_dir / "onboard-pre.json").write_text(json.dumps(pre, indent=2), encoding="utf-8")
    journal.execute("run-ci", [sys.executable, "-B", "tests/run_ci.py", "--platform", "linux",
                               "--shard", str(shard), "--shards", str(SHARDS), "--output", str(results_dir)],
                    ci_core=True)
    if shard == 1:
        journal.execute("tomlkit-pin", [sys.executable, "-m", "pip", "install", f"tomlkit=={MIN_TOMLKIT}"],
                        ci_core=True)
        journal.execute("tomlkit-compat", [sys.executable, "-B", "-m", "unittest",
                                           "tests.test_sbtd_codex_wiring", "tests.test_sbtd_followup_section_gate"],
                        ci_core=True)
        # Experiment-only restore: the real CI job is one-shot and never restores.
        journal.execute("tomlkit-restore", [sys.executable, "-m", "pip", "install",
                                            f"tomlkit=={declared_tomlkit}"])
    return finish_variant(journal, variant_dir, sha, tree, started_at, tick, pre, {"label": label})


def run_coverage_variant(variant, checkout, shard, output_dir):
    """Run one real shard under coverage; excluded from performance bounds."""
    checkout = Path(checkout)
    variant_dir = Path(output_dir) / variant
    results_dir = variant_dir / "results"
    coverage_dir = variant_dir / "coverage"
    snapshots_dir = variant_dir / "snapshots"
    for directory in (results_dir, coverage_dir, snapshots_dir):
        directory.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    journal = Recorder(variant_dir, checkout, env, timed=False)
    started_at = utcnow()
    sha = journal.text(journal.execute("git-sha", ["git", "rev-parse", "HEAD"]))
    env["VALIDATION_SHA"] = sha
    tree = journal.text(journal.execute("git-tree", ["git", "rev-parse", f"HEAD:{ONBOARD}"]))
    journal.execute("compileall", [sys.executable, "-m", "compileall", "-q", f"{ONBOARD}/scripts", "tests"])
    rcfile = variant_dir / "coverage.rc"
    rcfile.write_text("[run]\nrelative_files = True\n", encoding="utf-8")
    coverage_env = {"PYTHONDONTWRITEBYTECODE": "1", "COVERAGE_FILE": str(coverage_dir / "raw.dat")}
    pre = snapshot_source(checkout / ONBOARD)
    (snapshots_dir / "onboard-pre.json").write_text(json.dumps(pre, indent=2), encoding="utf-8")
    # Parent interpreter only: child CLIs stay real black-box behavior.
    journal.execute("coverage-run", [sys.executable, "-m", "coverage", "run", "--branch",
                                     f"--source={ONBOARD}/scripts", f"--rcfile={rcfile}",
                                     "tests/run_ci.py", "--platform", "linux", "--shard", str(shard),
                                     "--shards", str(SHARDS), "--output", str(results_dir)],
                    extra_env=coverage_env)
    coverage_json = coverage_dir / f"linux-coverage-{shard}.json"
    journal.execute("coverage-json", [sys.executable, "-m", "coverage", "json", f"--rcfile={rcfile}",
                                      "-o", str(coverage_json), "--pretty-print"],
                    extra_env=coverage_env)
    return finish_variant(journal, variant_dir, sha, tree, started_at, None, pre,
                          {"coverage_json": f"{variant}/coverage/linux-coverage-{shard}.json",
                           "coverage_rc": f"{variant}/coverage.rc"})


def pair_summary_md(report):
    yes_no = {True: "是", False: "否"}
    lines = [
        "# Linux 配对成本实验（临时脚手架，验证后删除）",
        "",
        f"- 结果：{'通过' if report['successful'] else '失败'}",
        (
            f"- 轮次：第 {report['round']} 轮（共 3 轮）；分片：{report['shard']}/{report['shards']}；"
            f"执行顺序：{' → '.join(report['order'])}"
        ),
        f"- 冻结基线 SHA：`{report['base_sha']}`",
    ]
    for label in report["order"]:
        variant = report["variants"][label]
        lines.append(
            f"- {label}：实际 SHA `{variant['git_sha']}`；变体总耗时 {variant['variant_elapsed_seconds']:.3f} 秒；"
            f"ci_core_seconds {variant['ci_core_seconds']:.3f} 秒（剔除实验专属 pip 恢复与元数据）；"
            f"输入漂移：{'无' if variant['drift']['equal'] else '有'}；"
            f"检出干净：{yes_no[variant['checkout_clean']]}；成功：{yes_no[variant['successful']]}")
    checks = report["checks"]
    lines.append(
        f"- 生产树（{ONBOARD}）两检出一致：{yes_no[checks['production_tree_equal']]}；"
        f"SHA 校验：{'通过' if checks['baseline_sha_matches_base'] and checks['candidate_sha_matches_github_sha'] else '失败'}")
    lines.append("- 本脚本仅记录原始配对测量：不把配对任务总耗时标注为任一单一变体的真实成本，不断言节省；"
                 "分片并集、状态与聚合由工作流外完成。")
    lines.append("- 逐命令原始 stdout/stderr：`<变体>/commands/`；原生 JSON／inventory／中文摘要："
                 "`<变体>/results/`；源快照：`<变体>/snapshots/`。")
    return "\n".join(lines) + "\n"


def coverage_summary_md(report):
    yes_no = {True: "是", False: "否"}
    run_rc = next((command["returncode"] for command in report["commands"]
                   if command["name"] == "coverage-run"), "缺失")
    lines = [
        "# Linux 覆盖率实验（临时脚手架，验证后删除）",
        "",
        f"- 结果：{'通过' if report['successful'] else '失败'}",
        f"- 变体／分片：{report['variant']}；{report['shard']}/{report['shards']}",
        f"- 实际 SHA：`{report['git_sha']}`（冻结基线 `{report['base_sha']}`）",
        f"- 原生 run_ci 返回码：{run_rc}（权威状态以原生 JSON 为准：`{report['variant']}/results/`）",
        (
            f"- 覆盖率 JSON：`{report['coverage_json']}`（source 相对路径，含 executed_lines／executed_branches；"
            "仅父解释器，子进程 CLI 保持真实黑盒行为）"
        ),
        (
            f"- 生产树（{ONBOARD}）：`{report['production_tree']}`；输入漂移：{'无' if report['drift']['equal'] else '有'}；"
            f"检出干净：{yes_no[report['checkout_clean']]}"
        ),
        "- 本作业不计入性能界限，单独计为实验开销；不含任何计时或性能声明。",
    ]
    return "\n".join(lines) + "\n"


def pair_main(args):
    checkouts = {"baseline": args.baseline.resolve(), "candidate": args.candidate.resolve()}
    output = args.output.resolve()
    for label, path in checkouts.items():
        if not (path / "tests" / "run_ci.py").is_file() or not (path / ONBOARD).is_dir():
            raise SystemExit(f"{label} checkout is incomplete: {path}")
    output.mkdir(parents=True, exist_ok=False)
    started_at = utcnow()
    tick = time.monotonic()
    metadata = capture_metadata(output)
    if not metadata["tomlkit_declared"]:
        raise SystemExit("tomlkit==<version> missing from pip freeze; cannot plan the TOML restore")
    order = ROUND_ORDERS[args.round]
    variants = {}
    for index, label in enumerate(order):
        record = run_ci_variant(label, checkouts[label], args.shard,
                                output / label, metadata["tomlkit_declared"])
        record["order_index"] = index
        variants[label] = record
    checks = {
        "baseline_sha_matches_base": variants["baseline"]["git_sha"] == BASE_SHA,
        "candidate_sha_matches_github_sha": (not os.environ.get("GITHUB_SHA")
                                             or variants["candidate"]["git_sha"] == os.environ["GITHUB_SHA"]),
        "production_tree_equal": (bool(variants["baseline"]["production_tree"])
                                  and variants["baseline"]["production_tree"]
                                  == variants["candidate"]["production_tree"]),
        "checkouts_clean": all(variant["checkout_clean"] for variant in variants.values()),
    }
    successful = all(variant["successful"] for variant in variants.values()) and all(checks.values())
    report = {
        "experiment": "linux-cost-experiment",
        "mode": "pair",
        "temporary": True,
        "platform": "linux",
        "round": args.round,
        "shard": args.shard,
        "shards": SHARDS,
        "order": list(order),
        "base_sha": BASE_SHA,
        "started_at": started_at,
        "finished_at": utcnow(),
        "pair_elapsed_seconds": round(time.monotonic() - tick, 3),
        "metadata": metadata,
        "checks": checks,
        "variants": variants,
        "successful": successful,
        "aggregation_note": "原始配对测量：不把配对任务总耗时标注为任一单一变体的真实成本，不断言节省；"
                            "分片并集、状态与聚合由工作流外完成。",
    }
    (output / "pair-summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "pair-summary.md").write_text(pair_summary_md(report), encoding="utf-8")
    print(f"Pair round={args.round} shard={args.shard}: "
          f"baseline ci_core={variants['baseline']['ci_core_seconds']:.3f}s "
          f"candidate ci_core={variants['candidate']['ci_core_seconds']:.3f}s "
          f"successful={successful}", flush=True)
    return 0 if successful else 1


def coverage_main(args):
    checkout = args.coverage_checkout.resolve()
    if not (checkout / "tests" / "run_ci.py").is_file() or not (checkout / ONBOARD).is_dir():
        raise SystemExit(f"coverage checkout is incomplete: {checkout}")
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    metadata = capture_metadata(output)
    record = run_coverage_variant(args.variant, checkout, args.shard, output)
    expected = BASE_SHA if args.variant == "baseline" else os.environ.get("GITHUB_SHA", "")
    checks = {"sha_matches_expected": not expected or record["git_sha"] == expected}
    report = {
        **record,
        "experiment": "linux-cost-experiment",
        "mode": "coverage",
        "temporary": True,
        "platform": "linux",
        "variant": args.variant,
        "shard": args.shard,
        "shards": SHARDS,
        "base_sha": BASE_SHA,
        "metadata": metadata,
        "checks": checks,
        "successful": record["successful"] and all(checks.values()),
        "coverage_note": "覆盖率作业不计入性能界限，单独计为实验开销；仅父解释器覆盖率；"
                         "无计时或性能声明。",
    }
    successful = report["successful"]
    (output / "coverage-summary.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    (output / "coverage-summary.md").write_text(coverage_summary_md(report), encoding="utf-8")
    native_coverage = output / report["coverage_json"]
    if native_coverage.is_file():
        native_coverage.with_suffix(".md").write_text(coverage_summary_md(report), encoding="utf-8")
    print(f"Coverage variant={args.variant} shard={args.shard}: successful={successful}", flush=True)
    return 0 if successful else 1


def main():
    os.umask(0o022)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--baseline", type=Path, help="Pair mode: checkout at the frozen base commit")
    parser.add_argument("--candidate", type=Path, help="Pair mode: checkout at github.sha")
    parser.add_argument("--coverage", dest="coverage_checkout", type=Path,
                        help="Coverage mode: single checkout to instrument")
    parser.add_argument("--variant", choices=("baseline", "candidate"),
                        help="Coverage mode: which variant --coverage holds")
    parser.add_argument("--round", type=int, choices=sorted(ROUND_ORDERS),
                        help="Pair mode: measurement round (order 1=AB, 2=BA, 3=AB)")
    parser.add_argument("--shard", type=int, choices=range(1, SHARDS + 1), required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.coverage_checkout is not None:
        if args.variant is None:
            parser.error("--coverage requires --variant")
        return coverage_main(args)
    missing = [name for name in ("baseline", "candidate", "round") if getattr(args, name) is None]
    if missing:
        parser.error("pair mode requires: " + ", ".join(f"--{name}" for name in missing))
    return pair_main(args)


if __name__ == "__main__":
    raise SystemExit(main())
