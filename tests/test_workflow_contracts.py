from __future__ import annotations

import hashlib
import copy
import json
import unittest
import subprocess
from html.parser import HTMLParser
from pathlib import Path

import jsonschema
import yaml


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "sbtd-workflow-onboard" / "templates" / "skills"


class WorkflowContractTests(unittest.TestCase):
    def test_repository_gitignore_keeps_canonical_generated_paths(self) -> None:
        entries = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()

        self.assertEqual(
            entries,
            [".DS_Store", ".gitnexus/", ".trellis/", "__pycache__/"],
        )

    def test_onboard_skill_is_discoverable_and_documents_npx_install(self) -> None:
        skill_path = ROOT / "sbtd-workflow-onboard" / "SKILL.md"
        skill = skill_path.read_text(encoding="utf-8")

        self.assertTrue(skill_path.is_file())
        self.assertIn("name: sbtd-workflow-onboard", skill)
        self.assertIn("npx skills add", skill)
        self.assertIn("--skill sbtd-workflow-onboard", skill)
        self.assertIn("--global", skill)

    def test_onboard_catalog_is_schema_valid_and_sources_exist(self) -> None:
        schema = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.schema.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        example = json.loads(
            (
                ROOT / "sbtd-workflow-onboard" / "examples" / "catalog.minimal.json"
            ).read_text(encoding="utf-8")
        )

        jsonschema.Draft202012Validator.check_schema(schema)
        jsonschema.Draft202012Validator(schema).validate(catalog)
        jsonschema.Draft202012Validator(schema).validate(example)
        ids = [entry["id"] for entry in catalog["entries"]]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(
            [
                entry["id"]
                for entry in catalog["entries"]
                if entry["kind"] == "bundled-skill"
            ],
            [
                "skill:sbtd-workflow-onboard",
                "skill:trellis-workflow",
                "skill:trellis-channel",
                "skill:project-validation",
                "skill:gherkin-bdd",
                "skill:knowledge-base-integration",
                "skill:maestro-mobile-e2e",
                "skill:lessons-record",
                "skill:book-refactoring-pass",
                "skill:book-legacy-change-safety",
                "skill:book-ddd-distilled-modeling",
                "skill:book-ddia-data-design",
                "skill:book-release-readiness",
                "skill:seo-geo",
            ],
        )
        self.assertEqual(
            [
                entry["id"]
                for entry in catalog["entries"]
                if entry["kind"] == "external-skill"
            ],
            [
                "skill:diagnosing-bugs",
                "skill:tdd",
                "skill:grill-me",
                "skill:grill-with-docs",
                "skill:grilling",
                "skill:domain-modeling",
                "skill:codebase-design",
                "skill:handoff",
                "skill:writing-great-skills",
                "skill:to-spec",
                "skill:to-tickets",
                "skill:ui-ux-pro-max",
                "skill:impeccable",
                "skill:web-ui-autotest-generator",
                "skill:shadcn",
            ],
        )
        onboard_root = ROOT / "sbtd-workflow-onboard"
        for entry in catalog["entries"]:
            with self.subTest(entry=entry["id"]):
                if entry["kind"] == "external-skill":
                    self.assertTrue(entry["source"]["repo"].startswith("https://"))
                    self.assertTrue(entry["source"]["subpath"])
                    self.assertIn(
                        entry["id"].removeprefix("skill:"),
                        entry["source"]["aliases"],
                    )
                    continue
                source = (onboard_root / entry["source"]).resolve()
                self.assertTrue(source.is_relative_to(onboard_root.resolve()))
                self.assertTrue(source.exists())

    def test_catalog_schema_rejects_escaping_source_paths(self) -> None:
        schema = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.schema.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        validator = jsonschema.Draft202012Validator(schema)
        cases = (
            ("skill:trellis-workflow", "source", "../outside"),
            ("skill:trellis-workflow", "source", "/tmp/outside"),
            ("skill:diagnosing-bugs", "subpath", "../outside"),
            ("skill:diagnosing-bugs", "subpath", "/tmp/outside"),
        )

        for entry_id, field, value in cases:
            with self.subTest(entry_id=entry_id, field=field, value=value):
                invalid = copy.deepcopy(catalog)
                entry = next(
                    item for item in invalid["entries"] if item["id"] == entry_id
                )
                if field == "subpath":
                    entry["source"][field] = value
                else:
                    entry[field] = value
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(invalid)

    def test_catalog_schema_rejects_kind_identity_and_role_mismatches(self) -> None:
        schema = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.schema.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        validator = jsonschema.Draft202012Validator(schema)
        cases = (
            ("skill:trellis-workflow", "id", "agent:trellis-workflow"),
            ("skill:trellis-workflow", "targetRole", "project-agents"),
            ("agent:codex-global", "id", "skill:codex-global"),
            ("agent:codex-global", "targetRole", "skill"),
        )

        for entry_id, field, value in cases:
            with self.subTest(entry_id=entry_id, field=field, value=value):
                invalid = copy.deepcopy(catalog)
                entry = next(
                    item for item in invalid["entries"] if item["id"] == entry_id
                )
                entry[field] = value
                with self.assertRaises(jsonschema.ValidationError):
                    validator.validate(invalid)

    def test_catalog_schema_rejects_malformed_https_repository_url(self) -> None:
        schema = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.schema.json").read_text(
                encoding="utf-8"
            )
        )
        catalog = json.loads(
            (ROOT / "sbtd-workflow-onboard" / "catalog.json").read_text(
                encoding="utf-8"
            )
        )
        validator = jsonschema.Draft202012Validator(schema)
        invalid = copy.deepcopy(catalog)
        external = next(
            item for item in invalid["entries"] if item["kind"] == "external-skill"
        )
        external["source"]["repo"] = "https://"

        with self.assertRaises(jsonschema.ValidationError):
            validator.validate(invalid)

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
            / "sbtd-workflow-onboard"
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
            "sbtd-workflow-onboard/templates/skills/"
            "knowledge-base-integration/scripts/knowledge_base_p1.py"
        )
        self.assertIn(repository_script, readme)
        self.assertIn(repository_script, readme_html)

        parser = HTMLParser()
        parser.feed(readme_html)
        parser.close()

    def test_version_check_prompt_is_versioned_and_documented(self) -> None:
        prompt_path = (
            ROOT / "prompts" / "automations" / "sbtd-workflow-tools-version-check.md"
        )
        prompt = prompt_path.read_text(encoding="utf-8")

        self.assertIn("SBTD Workflow Tools Version Check", prompt)
        self.assertIn("sbtd-workflow-onboard/catalog.json", prompt)
        self.assertIn("catalog.schema.json", prompt)
        self.assertIn("`__pycache__/`", prompt)
        self.assertIn("不要修改 `ENTRYPOINT.md`", prompt)
        self.assertIn("内容严格为四行", prompt)
        self.assertIn(
            "- `prompts/automations/sbtd-workflow-tools-version-check.md`",
            prompt,
        )
        self.assertIn(
            "`## <工具名> <起始版本> -> <目标版本>`",
            prompt,
        )
        for document_path in (
            ROOT / "README.md",
            ROOT / "README.html",
        ):
            with self.subTest(document=document_path.name):
                self.assertIn(
                    "prompts/automations/sbtd-workflow-tools-version-check.md",
                    document_path.read_text(encoding="utf-8"),
                )

    def test_tracked_controls_and_onboard_usage_are_documented(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_html = (ROOT / "README.html").read_text(encoding="utf-8")
        prompt = (
            ROOT / "prompts" / "automations" / "sbtd-workflow-tools-version-check.md"
        ).read_text(encoding="utf-8")

        self.assertLess(
            readme.index("## 安装及使用说明"),
            readme.index("## 仓库定位"),
        )
        bootstrap_command = (
            "npx --yes skills@latest add \\\n"
            "  https://github.com/KunoLu/640-skills \\\n"
            "  --skill sbtd-workflow-onboard \\\n"
            "  --global \\\n"
            "  --agent codex \\\n"
            "  --yes \\\n"
            "  --copy"
        )
        plan_command = (
            'python "$SBTD_ONBOARD_DIR/scripts/onboard.py" plan \\\n'
            "  --projects-root /abs/project-one,/abs/project-two \\\n"
            "  --json"
        )
        for document in (readme, readme_html):
            self.assertIn(bootstrap_command, document)
            self.assertIn(plan_command, document)
            self.assertIn("sbtd-workflow-onboard Skill", document)
            self.assertIn("AGENTS.md", document)
            self.assertIn("ENTRYPOINT.md", document)
            self.assertIn("SBTD Workflow Tools Version Check", document)
            self.assertIn("英语逗号", document)
            self.assertIn("--init-projects", document)
            self.assertIn("install.sh", document)
            self.assertIn("install.ps1", document)

        self.assertIn("非交互执行必须二选一", readme)
        self.assertIn(
            "project-only 模式只记录平台上下文，不执行任何全局检测或安装",
            readme_html,
        )
        self.assertIn("只有用户明确执行 `sync` / `同步` 时", prompt)
        self.assertIn("`update` / `更新` 与二者无关", prompt)
        self.assertIn("版本检查自动化不直接读取或写入 Orca live automation", prompt)
        self.assertNotIn("git check-ignore", prompt)
        self.assertNotIn("修改后必须同步更新同名 live automation", prompt)

        control_paths = (ROOT / "AGENTS.md", ROOT / "ENTRYPOINT.md")
        for control_path in control_paths:
            self.assertTrue(control_path.is_file())
        tracked = subprocess.run(
            ["git", "ls-files", "--", "AGENTS.md", "ENTRYPOINT.md"],
            cwd=ROOT,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.splitlines()
        self.assertEqual(set(tracked), {"AGENTS.md", "ENTRYPOINT.md"})

        agents = control_paths[0].read_text(encoding="utf-8")
        entrypoint = control_paths[1].read_text(encoding="utf-8")
        self.assertIn("必须由 Git 追踪", agents)
        self.assertNotIn("本地控制文件 Gate", agents)
        self.assertIn("README 与自动化 Prompt 同步规则", agents)
        self.assertIn("SBTD Workflow Tools Version Check", agents)
        self.assertIn("普通代码或文档修改只维护仓库内的版本化 prompt", agents)
        self.assertIn("只有用户明确执行 `sync` / `同步` 时", agents)
        self.assertIn("`update` / `更新` 不检查、不修改也不同步", agents)
        self.assertNotIn("即使本轮 prompt 内容没有变化", agents)
        self.assertNotIn("每次修改版本化 automation prompt 后", agents)
        self.assertIn("## 0. 版本监控配置", entrypoint)

    def test_readme_knowledge_cli_example_is_shell_executable(self) -> None:
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_html = (ROOT / "README.html").read_text(encoding="utf-8")
        invalid_pipeline = "knowledge_base_p1.py " + "|".join(
            ("validate-config", "decision", "ingest", "smoke")
        )
        executable_prefix = (
            "python sbtd-workflow-onboard/templates/skills/"
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
        design = (
            ROOT / "docs" / "prd" / "knowledge-base-integration-prd.md"
        ).read_text(encoding="utf-8")
        for document in (readme, design):
            self.assertIn("sync / 同步", document)
            self.assertIn("read / 读取", document)
        self.assertIn("P1.1", readme)
        self.assertIn("Runner Adapter", design)

    def test_caveman_auto_lite_is_task_scoped_and_protected(self) -> None:
        agents_root = ROOT / "sbtd-workflow-onboard" / "templates" / "agents"
        global_agents = (agents_root / "AGENTS.global.md").read_text(encoding="utf-8")
        project_agents = (agents_root / "AGENTS.project.md").read_text(encoding="utf-8")
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        readme_html = (ROOT / "README.html").read_text(encoding="utf-8")
        reference = (ROOT / "sbtd-workflow-onboard" / "REFERENCE.md").read_text(
            encoding="utf-8"
        )

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

    def test_gitignore_lessons_preserve_history_and_add_dated_status(self) -> None:
        repository_lesson = (
            ROOT / "docs" / "lessons" / "topics" / "repository-workflow.md"
        ).read_text(encoding="utf-8")
        validation_lesson = (
            ROOT / "docs" / "lessons" / "topics" / "validation-scripts.md"
        ).read_text(encoding="utf-8")

        self.assertIn(
            "违反本仓库 `.gitignore` 必须严格三行的规则",
            repository_lesson,
        )
        self.assertIn(
            "删除 `.pi/` 并保留 `.DS_Store`、`.gitnexus/`、`.trellis/` 三行",
            repository_lesson,
        )
        self.assertIn(
            "都要运行 `.gitignore` 精确三行检查",
            repository_lesson,
        )
        self.assertIn("状态更新（2026-07-16）", repository_lesson)
        self.assertIn(
            "并保留 `.gitignore` 三行校验，确认 `.DS_Store` 仍被忽略",
            validation_lesson,
        )
        self.assertIn("状态更新（2026-07-16）", validation_lesson)
        self.assertIn("状态更新（2026-07-18）", repository_lesson)
        self.assertIn("状态更新（2026-07-18）", validation_lesson)
        self.assertIn("恢复为 `.DS_Store`、`.gitnexus/`、`.trellis/`、`__pycache__/` 四行", repository_lesson)
        self.assertIn(
            "LESSON-20260718-required-controls-tracked-source",
            repository_lesson,
        )
        self.assertIn(
            "LESSON-20260718-automation-sync-trigger-separation",
            repository_lesson,
        )


if __name__ == "__main__":
    unittest.main()
