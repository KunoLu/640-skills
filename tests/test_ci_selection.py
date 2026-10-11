"""Behavioral guards against missing/duplicated CI tests or false-success reports."""
import io
import json
from pathlib import Path
import tempfile
import unittest

from tests.run_ci import RecordedResult, WINDOWS_CASES, partition, select_cases, verify_reports


class CaseIdentity:
    def __init__(self, identity):
        self.identity = identity

    def id(self):
        return self.identity


class CiSelectionTests(unittest.TestCase):
    def test_new_modules_are_included_once_and_module_fixtures_stay_together(self):
        cases = [CaseIdentity(name) for name in (
            "heavy.Tests.test_a", "heavy.Tests.test_b", "medium.Tests.test_a",
            "new_module.Tests.test_unanticipated", "small.Tests.test_a",
        )]
        shards = partition(cases, 3, {"heavy": 100, "medium": 30, "small": 1})
        actual = [case.id() for shard in shards for case in shard]
        self.assertCountEqual(actual, [case.id() for case in cases])
        self.assertEqual(len(actual), len(set(actual)))
        self.assertTrue(any({"heavy.Tests.test_a", "heavy.Tests.test_b"}.issubset(
            {case.id() for case in shard}) for shard in shards))

    def test_duplicate_identity_is_an_error_not_an_extra_execution(self):
        with self.assertRaisesRegex(ValueError, "Duplicate test identity"):
            partition([CaseIdentity("module.Tests.test_one")] * 2, 2, {})

    def test_windows_overlap_executes_once_and_keeps_native_boundaries(self):
        identities = list(WINDOWS_CASES) + [
            "test_sbtd_upgrade_hosts.ShellResourceTests.test_unicode_resolution_uses_utf8_even_with_legacy_console_encoding",
            "test_install_sh_agent_cli_flow.PowerShellInstallerAgentCliFlowTests.test_powershell_script_has_utf8_bom_for_windows_powershell",
            "test_install_sh_agent_cli_flow.BashInstallerAgentCliFlowTests.test_powershell_unknown_flag",
            "test_install_sh_agent_cli_flow.BashInstallerAgentCliFlowTests.test_bash_only",
            "test_sbtd_graft_entry.SessionRootResolutionTests.test_session_root",
            "test_workflow_contracts.WorkflowContractTests.test_native_ignore",
            "test_sbtd_probe_links.ProbeLinksTests.test_authorized_directory",
        ]
        selected = [case.id() for case in select_cases([CaseIdentity(i) for i in identities], "windows")]
        self.assertCountEqual(selected, [i for i in identities if not i.endswith("test_bash_only")])
        self.assertEqual(len(selected), len(set(selected)))

    def test_missing_required_windows_case_blocks_selection(self):
        with self.assertRaisesRegex(ValueError, "Required Windows cases missing"):
            select_cases([CaseIdentity(i) for i in WINDOWS_CASES[1:]], "windows")

    def test_class_setup_failure_cannot_be_reported_as_success(self):
        class BrokenSetup(unittest.TestCase):
            @classmethod
            def setUpClass(cls):
                raise RuntimeError("fixture setup failed")

            def test_not_reached(self):
                self.fail("setup should prevent this")

        result = unittest.TextTestRunner(stream=io.StringIO(), resultclass=RecordedResult).run(
            unittest.defaultTestLoader.loadTestsFromTestCase(BrokenSetup)
        )
        self.assertFalse(result.wasSuccessful())
        self.assertEqual(len(result.errors), 1)
        self.assertIn("fixture setup failed", result.errors[0][1])

    def test_aggregate_requires_complete_disjoint_same_revision_success(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            first = {
                "platform": "linux", "shard": 1, "shards": 2, "source_sha": "exact-sha",
                "successful": True, "scope": ["a", "b"], "selected": ["a"], "run_attempt": 1,
            }
            second = {**first, "shard": 2, "selected": ["b"]}
            (directory / "linux-1.json").write_text(json.dumps(first))
            path = directory / "linux-2.json"
            with self.assertRaises(FileNotFoundError):
                verify_reports(directory, "linux", 2, "exact-sha")
            path.write_text(json.dumps(second))
            self.assertEqual(verify_reports(directory, "linux", 2, "exact-sha"), 2)
            for change in (
                {"selected": ["a"]}, {"selected": []}, {"selected": ["outside"]},
                {"scope": ["a", "b", "missing"]}, {"source_sha": "old-sha"},
                {"successful": False}, {"shard": 1}, {"shards": 3},
            ):
                with self.subTest(change=change):
                    path.write_text(json.dumps({**second, **change}))
                    with self.assertRaises(ValueError):
                        verify_reports(directory, "linux", 2, "exact-sha")

    def test_partial_retry_retains_successful_shard_and_replaces_failed_attempt(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            initial = directory / "attempt-1"
            retry = directory / "attempt-2"
            initial.mkdir()
            retry.mkdir()
            common = {
                "platform": "linux", "shards": 2, "source_sha": "exact-sha",
                "scope": ["a", "b"], "run_attempt": 1, "successful": True,
            }
            (initial / "linux-1.json").write_text(json.dumps({**common, "shard": 1, "selected": ["a"]}))
            failed = {**common, "shard": 2, "selected": ["b"], "successful": False}
            (initial / "linux-2.json").write_text(json.dumps(failed))
            with self.assertRaises(ValueError):
                verify_reports(directory, "linux", 2, "exact-sha")
            repaired = {**failed, "run_attempt": 2, "successful": True}
            (retry / "linux-2.json").write_text(json.dumps(repaired))
            self.assertEqual(verify_reports(directory, "linux", 2, "exact-sha"), 2)
            # A newer failure must not be hidden by falling back to an older pass.
            failed_retry = {**common, "shard": 1, "selected": ["a"], "run_attempt": 2, "successful": False}
            (retry / "linux-1.json").write_text(json.dumps(failed_retry))
            with self.assertRaises(ValueError):
                verify_reports(directory, "linux", 2, "exact-sha")
