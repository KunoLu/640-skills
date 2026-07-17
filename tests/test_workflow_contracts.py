from __future__ import annotations

import hashlib
import json
import unittest
from html.parser import HTMLParser
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "kuno-workflow-onboard-skills" / "templates" / "skills"


class WorkflowContractTests(unittest.TestCase):
    def test_knowledge_integration_schemas_are_valid_draft_2020_12(self) -> None:
        schema_paths = list(
            (SKILLS / "knowledge-base-integration" / "references").glob("*.schema.json")
        )
        schema_paths.append(
            SKILLS
            / "project-validation"
            / "references"
            / "validation-evidence.schema.json"
        )

        self.assertGreater(len(schema_paths), 1)
        for schema_path in schema_paths:
            with self.subTest(schema=schema_path.name):
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                jsonschema.Draft202012Validator.check_schema(schema)

    def test_knowledge_ingest_requires_explicit_read_only_intent(self) -> None:
        gherkin = (SKILLS / "gherkin-bdd" / "SKILL.md").read_text(encoding="utf-8")
        project_agents = (
            ROOT
            / "kuno-workflow-onboard-skills"
            / "templates"
            / "agents"
            / "AGENTS.project.md"
        ).read_text(encoding="utf-8")

        for document in (gherkin, project_agents):
            self.assertIn("explicit read-only intent", document)
            self.assertIn("add / change / update / delete", document)
            self.assertIn("写入 / 新增 / 修改 / 更新 / 删除", document)

    def test_trellis_requires_post_commit_pr_head_evidence_refresh(self) -> None:
        trellis = (SKILLS / "trellis-workflow" / "SKILL.md").read_text(encoding="utf-8")
        contract = (
            SKILLS
            / "project-validation"
            / "references"
            / "validation-evidence-contract.md"
        ).read_text(encoding="utf-8")

        self.assertIn("post-commit evidence refresh", trellis)
        self.assertIn("final PR head SHA", trellis)
        self.assertIn("sidecar / envelope", trellis)
        self.assertIn("After the commit", contract)
        self.assertIn("final PR head SHA", contract)
        self.assertIn("sidecar or aggregate envelope", contract)

    def test_ci_evidence_envelope_is_schema_valid(self) -> None:
        schema_path = (
            SKILLS
            / "project-validation"
            / "references"
            / "validation-evidence.schema.json"
        )
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        envelope = {
            "schemaVersion": 1,
            "runId": "ci-smart-web-pr-123",
            "createdAt": "2026-07-17T00:00:00Z",
            "evidenceSource": "ci",
            "trigger": "pull-request",
            "repository": {
                "repositoryKey": "smart-web",
                "sourceRef": "refs/pull/123/head",
                "sourceCommit": "a" * 40,
                "worktreeState": "clean",
            },
            "sourceRevision": "exact",
            "environmentAlignment": "verified",
            "e2eMode": "full-stack",
            "mockStrategy": "none",
            "featureSources": [],
            "reports": [
                {
                    "testType": "web",
                    "path": "reports/web.html",
                    "summaryMd": "reports/web.md",
                    "sha256": "b" * 64,
                    "status": "passed",
                    "mode": "full-stack",
                }
            ],
            "evidencePublication": "published",
            "secretsRedacted": True,
        }

        jsonschema.Draft202012Validator(schema).validate(envelope)

        invalid_publication = {**envelope, "evidencePublication": "local-only"}
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(invalid_publication)

        invalid_checkout = {
            **envelope,
            "repository": {**envelope["repository"], "worktreeState": "dirty"},
        }
        with self.assertRaises(jsonschema.ValidationError):
            jsonschema.Draft202012Validator(schema).validate(invalid_checkout)

    def test_readme_uses_repository_root_script_path(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_html = (ROOT / "README.html").read_text(encoding="utf-8")
        repository_script = (
            "kuno-workflow-onboard-skills/templates/skills/"
            "knowledge-base-integration/scripts/knowledge_base_p1.py"
        )
        self.assertIn(repository_script, readme)
        self.assertIn(repository_script, readme_html)

        parser = HTMLParser()
        parser.feed(readme_html)
        parser.close()

    def test_readme_knowledge_cli_example_is_shell_executable(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_html = (ROOT / "README.html").read_text(encoding="utf-8")
        invalid_pipeline = "knowledge_base_p1.py " + "|".join(
            ("validate-config", "decision", "ingest", "smoke")
        )
        executable_prefix = (
            "python kuno-workflow-onboard-skills/templates/skills/"
            "knowledge-base-integration/scripts/knowledge_base_p1.py "
            "validate-config"
        )

        for document in (readme, readme_html):
            self.assertNotIn(invalid_pipeline, document)
            self.assertIn(executable_prefix, document)
            self.assertIn("--product", document)
            self.assertIn("--workspace", document)

    def test_p1_1_runtime_contract_and_runner_examples_are_complete(self) -> None:
        references = SKILLS / "knowledge-base-integration" / "references"
        runtime_contract = (references / "runtime-contract.md").read_text(
            encoding="utf-8"
        )
        workspace = yaml.safe_load(
            (references / "workspace.local.example.yaml").read_text(encoding="utf-8")
        )

        self.assertIn("P1.1 Runtime Contract", runtime_contract)
        self.assertIn("Schema compatibility", runtime_contract)
        self.assertIn("current and previous major", runtime_contract)
        command = workspace["runners"]["android-maestro"]["command"]
        self.assertIn("{job_manifest}", command)
        self.assertIn("{result_manifest}", command)
        self.assertIn("{artifact_dir}", command)

        for example_name, schema_name in (
            ("product.example.yaml", "product.schema.json"),
            ("workspace.local.example.yaml", "workspace.schema.json"),
            ("deployment-manifest.example.yaml", "deployment-manifest.schema.json"),
        ):
            with self.subTest(example=example_name):
                example = yaml.safe_load(
                    (references / example_name).read_text(encoding="utf-8")
                )
                schema = json.loads(
                    (references / schema_name).read_text(encoding="utf-8")
                )
                jsonschema.Draft202012Validator(schema).validate(example)

    def test_deployment_manifest_example_has_valid_canonical_digest(self) -> None:
        path = (
            SKILLS
            / "knowledge-base-integration"
            / "references"
            / "deployment-manifest.example.yaml"
        )
        manifest = yaml.safe_load(path.read_text(encoding="utf-8"))
        expected = manifest["attestation"].pop("manifest_digest")
        canonical = json.dumps(
            manifest, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        ).encode("utf-8")
        actual = "sha256:" + hashlib.sha256(canonical).hexdigest()
        self.assertEqual(expected, actual)

    def test_p1_1_documentation_keeps_sync_and_read_separate(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        design = (ROOT / "docs" / "knowledge-base-integration-prd.md").read_text(
            encoding="utf-8"
        )
        for document in (readme, design):
            self.assertIn("sync / 同步", document)
            self.assertIn("read / 读取", document)
        self.assertIn("P1.1", readme)
        self.assertIn("Runner Adapter", design)

    def test_caveman_auto_lite_is_task_scoped_and_protected(self) -> None:
        agents_root = (
            ROOT / "kuno-workflow-onboard-skills" / "templates" / "agents"
        )
        global_agents = (agents_root / "AGENTS.global.md").read_text(
            encoding="utf-8"
        )
        project_agents = (agents_root / "AGENTS.project.md").read_text(
            encoding="utf-8"
        )
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_html = (ROOT / "README.html").read_text(encoding="utf-8")
        reference = (
            ROOT / "kuno-workflow-onboard-skills" / "REFERENCE.md"
        ).read_text(encoding="utf-8")

        eligibility_clause = (
            "只有 `caveman` Skill 当前可见、用户没有明确退出、已知配置不是 "
            "`off`、当前输出属于重复且非阻塞的中间状态更新、任务范围稳定且没有等待"
            "用户决定时，才允许自动压缩。"
        )
        task_exit_clause = (
            "无论当前处于手动模式还是自动模式，都立即恢复正常输出，并在当前任务内禁止"
            "自动重入。"
        )
        task_reenable_clause = (
            "任务级自动退出只有在用户明确说 `本任务恢复自动压缩` 或 `重新启用自动压缩` "
            "时才清除；用户明确启动 `/caveman` 只进入手动模式，不清除任务级或会话级"
            "自动退出。"
        )
        session_exit_clause = (
            "会话级自动退出优先于任务级设置，只有用户明确说 `本会话重新启用自动压缩` "
            "时才清除。"
        )
        new_task_clause = (
            "新的用户请求到来时，任务级自动状态和任务级退出状态都重置，阈值从新任务"
            "重新计算；会话级自动退出继续有效。"
        )

        for clause in (
            eligibility_clause,
            task_exit_clause,
            task_reenable_clause,
            session_exit_clause,
            new_task_clause,
        ):
            self.assertIn(clause, global_agents)

        for phrase in (
            "auto-lite",
            "3 次或以上中间状态更新",
            "5 个或以上命令",
            "不得自动进入 `full`、`ultra`",
            "最终答复",
            "normal mode",
            "本任务不要自动压缩",
            "本会话关闭自动压缩",
            "不得停止或跳过必须的中间状态更新",
        ):
            self.assertIn(phrase, global_agents)

        self.assertIn("auto-lite", project_agents)
        self.assertIn("任务级", project_agents)
        self.assertIn("会话级自动退出优先于任务级设置", project_agents)
        self.assertIn("auto-lite", readme)
        self.assertIn("本任务恢复自动压缩", readme)
        self.assertIn("auto-lite", readme_html)
        self.assertIn("本会话重新启用自动压缩", readme_html)
        self.assertIn(
            "runtime thresholds may automatically enter task-scoped", reference
        )
        self.assertIn("session-level automatic opt-out takes precedence", reference)
        self.assertNotIn("达到全局阈值时只建议用户后续切换", readme)
        self.assertNotIn("达到全局阈值时只建议用户后续切换", readme_html)


if __name__ == "__main__":
    unittest.main()
