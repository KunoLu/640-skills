"""Run the native unittest scope once, with complete, disjoint CI shards."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import sys
import time
import unittest
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
UPGRADE_MODULES = (
    "test_onboard_upgrade", "test_sbtd_upgrade_inventory",
    "test_sbtd_upgrade_engine", "test_sbtd_upgrade_hosts",
)
MACOS_MODULES = UPGRADE_MODULES + (
    "test_onboard_multi_projects", "test_sbtd_graft_entry", "test_sbtd_codex_wiring",
    "test_sbtd_omp_wiring", "test_onboard_omp_wiring", "test_global_mcp_installation",
    "test_sbtd_graft_isolation",
)
WINDOWS_CASES = (
    "test_sbtd_followup_section_gate.FollowupSectionGateTests.test_omp_global_receipt_rejects_relative_runtime_paths",
    "test_sbtd_followup_section_gate.FollowupSectionGateTests.test_omp_historical_receipt_rejects_relative_runtime_paths",
    "test_sbtd_codex_wiring.CodexCandidateTests.test_discontiguous_tables_retire_only_owned_server_and_preserve_comments",
    "test_sbtd_codex_wiring.CodexCandidateTests.test_discontiguous_existing_global_server_is_byte_idempotent",
    "test_sbtd_codex_wiring.CodexCandidateTests.test_discontiguous_tables_keep_retirement_ownership_checks",
    "test_sbtd_migration_files.MigrationFileTests.test_windows_junction_is_rejected_before_snapshot_or_copy_reads_target",
    "test_sbtd_migration_files.MigrationFileTests.test_windows_private_directory_acl_gateway",
)


def flatten(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from flatten(item)
        else:
            yield item


def select_cases(cases, target):
    """Keep native platform boundaries while eliminating overlapping selectors."""
    if target == "linux":
        return list(cases)
    selected = []
    for case in cases:
        identity = case.id()
        module = identity.split(".")[0]
        installer = module == "test_install_sh_agent_cli_flow"
        if target == "macos":
            keep = module in MACOS_MODULES or (
                installer and ".BashInstallerAgentCliFlowTests." in identity
            )
        else:
            keep = module in UPGRADE_MODULES or identity in WINDOWS_CASES or (
                identity.startswith("test_sbtd_graft_entry.SessionRootResolutionTests.")
            ) or (installer and (
                ".PowerShellInstallerAgentCliFlowTests." in identity or "powershell" in identity
            ))
        # Workflow contracts include native Git-ignore behavior, not only prose.
        keep = keep or module in ("test_workflow_contracts", "test_sbtd_probe_links")
        if keep:
            selected.append(case)
    if target == "windows":
        missing = set(WINDOWS_CASES) - {case.id() for case in selected}
        if missing:
            raise ValueError(f"Required Windows cases missing: {sorted(missing)}")
    return selected


def partition(cases, count, weights):
    """Greedy module bins preserve class/module fixtures and discover new tests."""
    if count < 1:
        raise ValueError("Shard count must be positive")
    modules = {}
    identities = set()
    for case in cases:
        identity = case.id()
        if identity in identities:
            raise ValueError(f"Duplicate test identity: {identity}")
        identities.add(identity)
        modules.setdefault(identity.split(".")[0], []).append(case)
    bins = [[] for _ in range(count)]
    totals = [0.0] * count
    def weight(name):
        return weights.get(name, float(len(modules[name])))
    for name in sorted(modules, key=lambda name: (-weight(name), name)):
        slot = min(range(count), key=lambda index: (totals[index], index))
        bins[slot].extend(modules[name])
        totals[slot] += weight(name)
    return bins


class RecordedResult(unittest.TextTestResult):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.records = []
        self.row = None

    def startTest(self, test):
        self.started = time.monotonic()
        self.row = {"id": test.id(), "status": "passed"}
        super().startTest(test)

    def addSkip(self, test, reason):
        if self.row is not None:
            self.row.update(status="skipped", reason=reason)
        super().addSkip(test, reason)

    def addError(self, test, error):
        if self.row is not None:
            self.row.update(status="error")
        super().addError(test, error)

    def addFailure(self, test, error):
        self.row.update(status="failed")
        super().addFailure(test, error)

    def addSubTest(self, test, subtest, error):
        if error is not None:
            self.row.update(status="failed-subtest")
        super().addSubTest(test, subtest, error)

    def stopTest(self, test):
        self.row["seconds"] = time.monotonic() - self.started
        self.records.append(self.row)
        self.row = None
        super().stopTest(test)


def verify_reports(directory, target, count, sha):
    """Fail closed on absent, foreign-revision, overlapping or incomplete shards."""
    if not sha:
        raise ValueError("An exact validation SHA is required")
    scope = None
    selected = []
    for index in range(1, count + 1):
        candidates = []
        for path in directory.rglob(f"{target}-{index}.json"):
            report = json.loads(path.read_text(encoding="utf-8"))
            attempt = report["run_attempt"]
            if type(attempt) is not int or attempt < 1 or report["source_sha"] != sha:
                raise ValueError(f"Invalid native run identity: {path}")
            candidates.append((attempt, path, report))
        if not candidates:
            raise FileNotFoundError(f"Missing {target} shard {index}")
        newest = max(item[0] for item in candidates)
        latest = [item for item in candidates if item[0] == newest]
        if len(latest) != 1:
            raise ValueError(f"Ambiguous {target} shard {index} attempt {newest}")
        _, path, report = latest[0]
        if (report["source_sha"] != sha or report["platform"] != target
                or report["shard"] != index or report["shards"] != count
                or report["successful"] is not True):
            raise ValueError(f"Unsuccessful or mismatched shard: {path.name}")
        if scope is None:
            scope = report["scope"]
        if report["scope"] != scope or not report["selected"]:
            raise ValueError(f"Inconsistent or empty shard: {path.name}")
        selected.extend(report["selected"])
    if scope is None or len(scope) != len(set(scope)):
        raise ValueError("Invalid full scope")
    if len(selected) != len(set(selected)) or set(selected) != set(scope):
        raise ValueError("Shard union is incomplete or overlapping")
    return len(scope)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--platform", choices=("linux", "macos", "windows"), required=True)
    parser.add_argument("--shard", type=int, default=1)
    parser.add_argument("--shards", type=int, default=1)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--list", action="store_true", help="Emit selected IDs without executing tests")
    parser.add_argument("--verify-reports", action="store_true", help="Verify the complete downloaded shard union")
    args = parser.parse_args()
    if not 1 <= args.shard <= args.shards:
        parser.error("shard must be in 1..shards")
    if args.verify_reports:
        count = verify_reports(args.output, args.platform, args.shards, os.environ.get("VALIDATION_SHA"))
        print(f"Verified {count} distinct tests across all {args.shards} successful {args.platform} shards")
        return 0
    sys.path.insert(0, str(ROOT))
    loader = unittest.TestLoader()
    discovered = list(flatten(loader.discover(str(ROOT / "tests"), pattern="test_*.py")))
    if loader.errors:
        parser.error("Test discovery failed:\n" + "\n".join(loader.errors))
    cases = select_cases(discovered, args.platform)
    weights = json.loads((ROOT / ".github" / "test-weights.json").read_text(encoding="utf-8"))
    shards = partition(cases, args.shards, weights[args.platform])
    selected = shards[args.shard - 1]
    if not selected:
        parser.error("Empty required shard")
    args.output.mkdir(parents=True, exist_ok=True)
    prefix = args.output / f"{args.platform}-{args.shard}"
    started = datetime.now(timezone.utc).isoformat()
    manifest = {"platform": args.platform, "shard": args.shard, "shards": args.shards,
                "scope": sorted(case.id() for case in cases), "selected": [case.id() for case in selected]}
    prefix.with_suffix(".inventory.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.list:
        print(json.dumps(manifest, indent=2))
        return 0
    tick = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(unittest.TestSuite(selected))
    report = {**manifest, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
              "seconds": time.monotonic() - tick, "python": sys.version, "environment": platform.platform(),
              "source_sha": os.environ.get("VALIDATION_SHA"), "successful": result.wasSuccessful(),
              "evidence_source": "ci" if os.environ.get("GITHUB_ACTIONS") == "true" else "developer-local",
              "run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
              "tests": result.testsRun, "skipped": len(result.skipped), "cases": result.records,
              "failures": [(test.id(), message) for test, message in result.failures + result.errors]}
    prefix.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    prefix.with_suffix(".md").write_text(
        f"# 原生 CI 分片验证\n\n- 结果：{'通过' if result.wasSuccessful() else '失败'}\n"
        f"- 平台／分片：{args.platform} {args.shard}/{args.shards}\n"
        f"- SHA：`{report['source_sha']}`\n- 测试：{result.testsRun}；skip：{len(result.skipped)}\n"
        f"- 原生运行 attempt：{report['run_attempt']}；聚合允许同 SHA 的成功分片保留其真实较早 attempt。\n"
        f"- 耗时：{report['seconds']:.3f} 秒\n- 逐例结果、skip 原因及失败详情：同 stem JSON。\n"
        f"- Evidence Source: {report['evidence_source']}；rtk: skipped-for-report。\n"
        "- 仅证明此分片；全部必需分片及最低 TOML 依赖检查通过才通过聚合门禁。\n",
        encoding="utf-8",
    )
    print(f"Shard {args.shard}/{args.shards}: {result.testsRun} tests in {report['seconds']:.3f}s")
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
