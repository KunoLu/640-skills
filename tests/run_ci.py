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
    "test_sbtd_upgrade_retirement",
    "test_sbtd_cleanup_upgrade", "test_sbtd_cleanup_upgrade_integration",
    "test_onboard_windows_platform",
)
MACOS_MODULES = UPGRADE_MODULES + (
    "test_onboard_multi_projects", "test_global_mcp_installation",
    "test_onboard_external_skills",
)
WINDOWS_CASES = (
    "test_sbtd_omp_agents_target.BuildOperationsTargetTests.test_profile_targets_profile_agent_dir",
    "test_sbtd_migration_files.MigrationFileTests.test_windows_junction_is_rejected_before_snapshot_or_copy_reads_target",
    "test_sbtd_migration_files.MigrationFileTests.test_windows_private_directory_acl_gateway",
    "test_sbtd_migration_files.MigrationFileTests.test_windows_native_acl_proof_matches_the_powershell_oracle",
    "test_sbtd_migration_files.MigrationFileTests.test_windows_native_acl_distinguishes_empty_null_and_unreadable_dacls",
    "test_sbtd_migration_files.WindowsRetirementPermissionTests.test_protected_file_permissions_survive_writes_removal_and_restore",
    "test_sbtd_migration_files.WindowsRetirementPermissionTests.test_unprotected_inherited_dacl_survives_a_write",
    "test_sbtd_migration_files.WindowsRetirementPermissionTests.test_null_and_empty_dacls_never_authorize_a_live_write",
    "test_sbtd_migration_files.WindowsRetirementPermissionTests.test_unassignable_owner_cannot_publish_a_candidate",
    "test_sbtd_migration_files.WindowsRetirementPermissionTests.test_publication_preserves_a_recreated_target_and_held_original",
    "test_sbtd_upgrade_retirement.RealRetirementUpgradeTests.test_windows_native_retirement_edit_and_remove_restore_permissions",
    "test_sbtd_retirement.RetirementProofTests.test_windows_remove_and_restore_preserves_native_descriptor",
    "test_sbtd_cleanup_legacy.RetirementArtifactTests.test_windows_reset_retry_refuses_acl_only_drift",
    "test_sbtd_cleanup_legacy.RetirementArtifactTests.test_windows_composed_cleanup_binds_acl_on_apply_retry_and_rollback",
    "test_sbtd_cleanup_legacy.RetirementArtifactTests.test_windows_vendor_overlap_blocks_before_execution",
    "test_sbtd_migration_files.MigrationFileTests.test_directory_removal_keeps_later_user_edit_and_new_file",
    "test_sbtd_migration_files.MigrationFileTests.test_directory_removal_preserves_replaced_capture_directory",
    "test_sbtd_migration_files.MigrationFileTests.test_directory_removal_reports_disappearing_holder_without_deleting_files",
    "test_sbtd_migration_files.MigrationFileTests.test_directory_removal_stops_when_holder_gains_unknown_content",
    "test_sbtd_migration_files.MigrationFileTests.test_conflicting_restore_reports_the_retained_object_without_overwriting",
    # The real cmd.exe shim execution pair is the only on-Windows proof of the
    # M03/M04 launcher fix; selection without execution must not pass.
    "test_onboard_windows_platform.WindowsShimExecutionTests.test_check_cli_tool_executes_cmd_shim_found_on_path",
    "test_onboard_windows_platform.WindowsShimExecutionTests.test_project_command_executes_cmd_shim_found_on_path",
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
                installer and (".PowerShellInstallerAgentCliFlowTests." in identity or "powershell" in identity)
            )
        # Workflow contracts include native Git-ignore behavior, not only prose.
        keep = keep or module in (
            "test_workflow_contracts", "test_sbtd_probe_links",
            "test_sbtd_omp_sources", "test_sbtd_retirement",
        )
        if keep:
            selected.append(case)
    if target == "windows":
        missing = set(WINDOWS_CASES) - {case.id() for case in selected}
        if missing:
            raise ValueError(f"Required Windows cases missing: {sorted(missing)}")
    return selected


def fixture_unit(case):
    """Cases sharing a module or class fixture must run in one shard."""
    kind = type(case)
    module = sys.modules.get(kind.__module__)
    if hasattr(module, "setUpModule") or hasattr(module, "tearDownModule"):
        return kind.__module__
    base = unittest.TestCase
    if isinstance(case, base) and any(
        getattr(getattr(kind, name), "__func__", getattr(kind, name))
        is not getattr(base, name).__func__
        for name in ("setUpClass", "tearDownClass")
    ):
        return f"{kind.__module__}.{kind.__qualname__}"
    return case.id()


def fallback_weight(weights):
    """Median measured case seconds; never zero, so new tests still count."""
    known = sorted(weights.values())
    return max(known[len(known) // 2], 0.001) if known else 1.0


def unweighted(cases, weights):
    return sorted(case.id() for case in cases if case.id() not in weights)


def partition(cases, count, weights):
    """Greedy bins over fixture units: single cases unless a fixture binds them."""
    if count < 1:
        raise ValueError("Shard count must be positive")
    units = {}
    order = {}
    for index, case in enumerate(cases):
        identity = case.id()
        if identity in order:
            raise ValueError(f"Duplicate test identity: {identity}")
        order[identity] = index
        units.setdefault(fixture_unit(case), []).append(case)
    fallback = fallback_weight(weights)
    unit_weights = {
        name: sum(weights.get(case.id(), fallback) for case in members)
        for name, members in units.items()
    }
    bins = [[] for _ in range(count)]
    totals = [0.0] * count
    for name in sorted(units, key=lambda name: (-unit_weights[name], name)):
        slot = min(range(count), key=lambda index: (totals[index], index))
        bins[slot].extend(units[name])
        totals[slot] += unit_weights[name]
    return [sorted(shard, key=lambda case: order[case.id()]) for shard in bins]


def latest_reports(directory, target):
    """Newest attempt of every shard report found under ``directory``."""
    candidates = {}
    for path in directory.rglob(f"{target}-*.json"):
        stem = path.stem.removeprefix(f"{target}-")
        if not stem.isdigit():
            continue
        if stem != str(int(stem)):
            raise ValueError(f"Noncanonical native shard filename: {path.name}")
        report = json.loads(path.read_text(encoding="utf-8"))
        attempt = report["run_attempt"]
        if type(attempt) is not int or attempt < 1:
            raise ValueError(f"Invalid native run attempt: {path}")
        candidates.setdefault(int(stem), []).append(report)
    newest = []
    for index in sorted(candidates):
        reports = candidates[index]
        attempt = max(report["run_attempt"] for report in reports)
        latest = [report for report in reports if report["run_attempt"] == attempt]
        if len(latest) != 1:
            raise ValueError(f"Ambiguous {target} shard {index} attempt {attempt}")
        newest.append(latest[0])
    return newest


def measured_weights(directory, target):
    """Per-case native seconds from one revision's complete, successful shards."""
    reports = latest_reports(directory, target)
    if not reports:
        raise FileNotFoundError(f"No {target} shard reports under {directory}")
    revisions = {report["source_sha"] for report in reports}
    if len(revisions) != 1:
        raise ValueError("Weights need successful shards from exactly one revision")
    sha = revisions.pop()
    if not sha:
        raise ValueError("Weights need an exact source revision")
    if len(reports) != reports[0]["shards"]:
        raise ValueError("Weights need exactly the declared shard set")
    verify_reports(directory, target, reports[0]["shards"], sha)
    seconds = {}
    for report in reports:
        measured = [row["id"] for row in report["cases"]]
        if len(measured) != len(set(measured)) or set(measured) != set(report["selected"]):
            raise ValueError("Weights need exactly one measurement per selected case")
        for row in report["cases"]:
            if row["id"] in seconds:
                raise ValueError("Weights contain a repeated measured case")
            seconds[row["id"]] = round(row["seconds"], 3)
    if set(seconds) != set(reports[0]["scope"]):
        raise ValueError("Weights need the complete measured scope")
    return sha, dict(sorted(seconds.items()))


def required_native_cases(target, identities):
    """Critical native checks must execute, not merely be selected and skipped."""
    required = set()
    case_sensitive = "test_sbtd_upgrade_inventory.PhysicalTargetPlanTests.test_case_sensitive_onboard_provider_uses_selected_installation"
    if target == "windows":
        required.update(WINDOWS_CASES)
        required.update((
            case_sensitive,
            "test_sbtd_upgrade_hosts.ShellResourceTests.test_windows_unicode_profile_is_not_executed_by_probe",
            "test_sbtd_upgrade_hosts.ShellResourceTests.test_windows_profile_is_not_rewritten_by_upgrade",
        ))
        required.update(identity for identity in identities
                        if identity.startswith("test_install_sh_agent_cli_flow.") and "powershell" in identity)
    elif target == "linux":
        required.update((
            case_sensitive,
            "test_onboard_contracts.PathAliasContainmentTests.test_public_contract_keeps_distinct_case_sensitive_targets_separate",
        ))
    return required


def unpassed_required(required, records):
    return sorted(set(required) - {row["id"] for row in records if row["status"] == "passed"})


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

    def addExpectedFailure(self, test, error):
        self.row.update(status="expected-failure")
        super().addExpectedFailure(test, error)

    def addUnexpectedSuccess(self, test):
        self.row.update(status="unexpected-success")
        super().addUnexpectedSuccess(test)

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
    parser.add_argument("--refresh-weights", action="store_true",
                        help="Rewrite this platform's scheduling weights from downloaded shard reports")
    args = parser.parse_args()
    if not 1 <= args.shard <= args.shards:
        parser.error("shard must be in 1..shards")
    weights_path = ROOT / ".github" / "test-weights.json"
    if args.refresh_weights:
        sha, seconds = measured_weights(args.output, args.platform)
        weights = json.loads(weights_path.read_text(encoding="utf-8"))
        weights[args.platform] = seconds
        weights["_measurement"][args.platform] = {"source_sha": sha, "cases": len(seconds)}
        weights_path.write_text(json.dumps(weights, indent=2) + "\n", encoding="utf-8")
        print(f"Recorded {len(seconds)} {args.platform} case weights from {sha}")
        return 0
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
    weights = json.loads(weights_path.read_text(encoding="utf-8")).get(args.platform, {})
    shards = partition(cases, args.shards, weights)
    selected = shards[args.shard - 1]
    if not selected:
        parser.error("Empty required shard")
    args.output.mkdir(parents=True, exist_ok=True)
    prefix = args.output / f"{args.platform}-{args.shard}"
    started = datetime.now(timezone.utc).isoformat()
    manifest = {"platform": args.platform, "shard": args.shard, "shards": args.shards,
                "scope": sorted(case.id() for case in cases), "selected": [case.id() for case in selected],
                "unweighted": unweighted(cases, weights) if args.shards > 1 else []}
    required = required_native_cases(args.platform, manifest["scope"])
    if required - set(manifest["scope"]):
        parser.error("Required native cases are missing from discovery")
    prefix.with_suffix(".inventory.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    if args.list:
        print(json.dumps(manifest, indent=2))
        return 0
    tick = time.monotonic()
    result = unittest.TextTestRunner(verbosity=2, resultclass=RecordedResult).run(unittest.TestSuite(selected))
    native_failures = unpassed_required(required.intersection(manifest["selected"]), result.records)
    successful = result.wasSuccessful() and not native_failures
    report = {**manifest, "started_at": started, "finished_at": datetime.now(timezone.utc).isoformat(),
              "seconds": time.monotonic() - tick, "python": sys.version, "environment": platform.platform(),
              "source_sha": os.environ.get("VALIDATION_SHA"), "successful": successful,
              "evidence_source": "ci" if os.environ.get("GITHUB_ACTIONS") == "true" else "developer-local",
              "run_attempt": int(os.environ.get("GITHUB_RUN_ATTEMPT", "1")),
              "tests": result.testsRun, "skipped": len(result.skipped), "cases": result.records,
              "required_native_failures": native_failures,
              "skip_details": [(test.id(), reason) for test, reason in result.skipped],
              "failures": [(test.id(), message) for test, message in result.failures + result.errors]}
    prefix.with_suffix(".json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    prefix.with_suffix(".md").write_text(
        f"# 原生 CI 分片验证\n\n- 结果：{'通过' if successful else '失败'}\n"
        f"- 平台／分片：{args.platform} {args.shard}/{args.shards}\n"
        f"- SHA：`{report['source_sha']}`\n- 测试：{result.testsRun}；skip：{len(result.skipped)}\n"
        f"- 原生运行 attempt：{report['run_attempt']}；聚合允许同 SHA 的成功分片保留其真实较早 attempt。\n"
        f"- 耗时：{report['seconds']:.3f} 秒\n- 逐例结果、skip 原因及失败详情：同 stem JSON。\n"
        f"- 缺少调度权重的用例：{len(manifest['unweighted'])}（按中位数估算，仍全部执行；清单见 inventory）。\n"
        f"- Evidence Source: {report['evidence_source']}；rtk: skipped-for-report。\n"
        "- 仅证明此分片；全部必需分片及最低 TOML 依赖检查通过才通过聚合门禁。\n",
        encoding="utf-8",
    )
    print(f"Shard {args.shard}/{args.shards}: {result.testsRun} tests in {report['seconds']:.3f}s")
    if native_failures:
        print("Required native checks did not pass: " + ", ".join(native_failures), file=sys.stderr)
    return 0 if successful else 1


if __name__ == "__main__":
    raise SystemExit(main())
