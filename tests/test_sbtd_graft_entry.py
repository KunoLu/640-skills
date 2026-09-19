from __future__ import annotations

import json
import os
import subprocess
import stat
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPTS = Path(__file__).resolve().parents[1] / "sbtd-workflow-onboard/scripts"
sys.path.insert(0, str(SCRIPTS))

from onboard_contracts import ContractError
from sbtd_graft_entry import validate_build_scope, validate_project
from sbtd_migration_files import snapshot


def project_fixture(base):
    root = base / "project"
    (root / "graft/.graph").mkdir(parents=True)
    (root / "graft/.cache").mkdir()
    (root / "graft/.graph/wiring.json").write_text('{"fixture":true}\n')
    stamp = {
        "version": "0.18.0",
        "hosts": ["agents"],
        "opts": {"global": False, "mcp": False, "hooks": False, "statusline": False},
        "at": "2026-09-19T00:00:00Z",
    }
    (root / "graft/.cache/wiring-stamp.json").write_text(json.dumps(stamp))
    return root


class GuardedLaunchTests(unittest.TestCase):
    def test_missing_or_old_stamp_never_repairs_itself(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            original = snapshot(base)
            self.assertEqual(validate_project(root)["root"], str(root))
            self.assertEqual(snapshot(base), original)
            path = root / "graft/.cache/wiring-stamp.json"
            stamp = json.loads(path.read_text())
            stamp["version"] = "0.17.0"
            path.write_text(json.dumps(stamp))
            before = snapshot(base)
            with self.assertRaises(ContractError):
                validate_project(root)
            self.assertEqual(snapshot(base), before)
            path.unlink()
            before = snapshot(base)
            with self.assertRaises(ContractError):
                validate_project(root)
            self.assertEqual(snapshot(base), before)

    def test_internal_graph_symlink_does_not_claim_business_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = project_fixture(Path(directory).resolve())
            graph = root / "graft"
            business = root / "business-data"
            graph.rename(business)
            graph.symlink_to(business, target_is_directory=True)
            with self.assertRaises(ContractError):
                validate_project(root)
            self.assertTrue(graph.is_symlink())
            self.assertTrue((business / ".graph/wiring.json").is_file())

    def test_real_launcher_child_receives_only_safe_project_and_home_overrides(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            home = base / "home"
            home.mkdir(mode=0o700)
            package = base / "node_modules/@nanonets/graft"
            (package / "dist").mkdir(parents=True)
            (package / "package.json").write_text(
                '{"name":"@nanonets/graft","version":"0.18.0"}'
            )
            cli = package / "dist/cli.js"
            cli.write_text(
                'import json,os\nprint(json.dumps({key:os.environ.get(key) for key in ("HOME","DO_NOT_TRACK","DNT","GRAFT_DIR","GRAFT_NO_REFRESH","CLAUDE_PROJECT_DIR","OPENAI_API_KEY","GRAFT_API_KEY","NODE_OPTIONS")}))\n'
            )
            environment = {
                **os.environ,
                "HOME": str(home),
                "USERPROFILE": str(home),
                "OPENAI_API_KEY": "synthetic-secret",
                "GRAFT_API_KEY": "synthetic-secret",
                "NODE_OPTIONS": "synthetic-preload",
                "CLAUDE_PROJECT_DIR": str(base / "unselected"),
            }
            before = snapshot(home)
            completed = subprocess.run(
                [
                    sys.executable,
                    "-B",
                    str(SCRIPTS / "sbtd_graft_entry.py"),
                    "mcp",
                    "--root",
                    str(root),
                    "--node",
                    str(Path(sys.executable).resolve()),
                    "--entry",
                    str(cli),
                ],
                env=environment,
                text=True,
                capture_output=True,
                timeout=20,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            observed = json.loads(completed.stdout)
            self.assertEqual(observed["GRAFT_NO_REFRESH"], "1")
            self.assertEqual(observed["DO_NOT_TRACK"], "1")
            self.assertEqual(observed["DNT"], "1")
            self.assertEqual(observed["GRAFT_DIR"], str(root / "graft"))
            self.assertEqual(observed["CLAUDE_PROJECT_DIR"], str(root))
            for key in ("OPENAI_API_KEY", "GRAFT_API_KEY", "NODE_OPTIONS"):
                self.assertIsNone(observed[key])
            self.assertNotEqual(observed["HOME"], str(home))
            self.assertFalse(Path(observed["HOME"]).exists())
            self.assertEqual(snapshot(home), before)


def graph_node(path, span="L1-L3"):
    return {
        "id": path,
        "name": path.rsplit("/", 1)[-1],
        "kind": "file",
        "path": path,
        "span": span,
        "signature": None,
        "exported": True,
        "origin": "ast",
        "body_hash": "hash",
        "summary_state": "pending",
        "summary": None,
        "crux": None,
    }


def write_graph(root, payload):
    (root / "graft/.graph/wiring.json").write_text(json.dumps(payload) + "\n")


class BuildScopeGuardTests(unittest.TestCase):
    def assert_refused_readonly(self, base, check):
        def observed():
            entries = {}
            for directory, children, files in os.walk(base, followlinks=False):
                for name in children + files:
                    path = Path(directory) / name
                    mode = path.lstat().st_mode
                    content = (
                        os.readlink(path)
                        if stat.S_ISLNK(mode)
                        else (path.read_bytes() if stat.S_ISREG(mode) else None)
                    )
                    entries[str(path.relative_to(base))] = (mode, content)
            return entries

        before = observed()
        with self.assertRaises(ContractError):
            check()
        self.assertEqual(observed(), before)

    def test_explicit_build_state_without_graph_is_valid(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = base / "project"
            root.mkdir()
            self.assertIsNone(validate_build_scope(root))
            (root / "graft").mkdir()
            self.assertIsNone(validate_build_scope(root))
            (root / "src").mkdir()
            (root / "src/a.ts").write_text("export const a = 1;\n")
            self.assertIsNone(validate_build_scope(root))

    def test_workspace_index_refused_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            index = root / "graft/workspace.json"
            for payload in (
                '{"version":1,"children":["../sibling"]}',
                "not even json",
            ):
                index.write_text(payload)
                self.assert_refused_readonly(base, lambda: validate_build_scope(root))
                self.assert_refused_readonly(base, lambda: validate_project(root))
                index.unlink()

    def test_workspace_parent_invocation_refused_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            for name in ("repoA", "repoB"):
                (root / name / ".git").mkdir(parents=True)
            self.assert_refused_readonly(base, lambda: validate_build_scope(root))
            self.assert_refused_readonly(base, lambda: validate_project(root))
            # An own .git makes the same children an ordinary repo, which the
            # pinned package never treats as a workspace build root.
            (root / ".git").mkdir()
            self.assertIsNone(validate_build_scope(root))

    def test_generated_tree_link_hardlink_special_refused_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            victim = base / "victim.md"
            victim.write_text("original foreign bytes\n")
            (root / "graft/INDEX.md").symlink_to(victim)
            self.assert_refused_readonly(base, lambda: validate_build_scope(root))
            self.assertEqual(victim.read_text(), "original foreign bytes\n")
            (root / "graft/INDEX.md").unlink()
            origin = base / "origin.md"
            origin.write_text("shared inode\n")
            os.link(origin, root / "graft/hardlinked.md")
            self.assert_refused_readonly(base, lambda: validate_build_scope(root))
            (root / "graft/hardlinked.md").unlink()
            if hasattr(os, "mkfifo"):
                os.mkfifo(root / "graft/pipe")
                self.assert_refused_readonly(base, lambda: validate_build_scope(root))
                (root / "graft/pipe").unlink()
            self.assertIsNone(validate_build_scope(root))

    def test_poisoned_graph_paths_and_spans_refused_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            poisons = [
                {"nodes": [graph_node("../evil.ts")]},
                {"nodes": [graph_node("/etc/passwd")]},
                {"nodes": [graph_node("src/a.ts", span="../..:L1-L2")]},
                {"nodes": [graph_node("src/a.ts", span="L1-")]},
                {
                    "nodes": [],
                    "edges": [
                        {
                            "source": "s",
                            "target": "../../etc/passwd:L1-L2",
                            "relation": "imports",
                            "confidence": "extracted",
                        }
                    ],
                },
                {
                    "nodes": [],
                    "edges": [
                        {
                            "source": "/etc/passwd:L1-L2",
                            "target": "t",
                            "relation": "contains",
                            "confidence": "extracted",
                        }
                    ],
                },
            ]
            for payload in poisons:
                with self.subTest(payload=payload):
                    write_graph(root, payload)
                    self.assert_refused_readonly(
                        base, lambda: validate_build_scope(root)
                    )
            self.assertEqual(
                json.loads((root / "graft/.graph/wiring.json").read_text()),
                poisons[-1],
            )

    def test_source_links_and_hardlinks_refused_but_missing_permitted(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            (root / "src").mkdir()
            (root / "src/a.ts").write_text("export const a = 1;\n")
            (root / "src/link.ts").symlink_to(root / "src/a.ts")
            os.link(root / "src/a.ts", root / "src/hard.ts")
            for path in ("src/link.ts", "src/hard.ts"):
                with self.subTest(path=path):
                    write_graph(root, {"nodes": [graph_node(path)]})
                    self.assert_refused_readonly(
                        base, lambda: validate_build_scope(root)
                    )
            # Restoring single-link src/a.ts for the valid graph below (the
            # hardlink refusal check raised both inodes' link counts).
            (root / "src/hard.ts").unlink()
            write_graph(
                root,
                {
                    "nodes": [
                        graph_node("src/a.ts"),
                        graph_node("src/gone.ts"),
                    ],
                    "edges": [
                        {
                            "source": "src/a.ts",
                            "target": "lodash",
                            "relation": "imports",
                            "confidence": "extracted",
                        },
                        {
                            "source": "s",
                            "target": "src/a.ts:L1-L3",
                            "relation": "contains",
                            "confidence": "extracted",
                        },
                    ],
                },
            )
            self.assertIsNone(validate_build_scope(root))
            self.assertIsNotNone(validate_project(root)["stamp"])

    def test_poisoned_extract_cache_refused_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            (root / "src").mkdir()
            (root / "src/a.ts").write_text("export const a = 1;\n")
            cache = root / "graft/.cache/extract.0123456789abcdef.json"
            entry = {"size": 18, "mtimeMs": 1, "hash": "hash"}
            poisons = [
                {
                    "files": {
                        "src/a.ts": {
                            **entry,
                            "nodes": [graph_node("../evil.ts")],
                            "rawEdges": [],
                        }
                    }
                },
                {
                    "files": {
                        "src/a.ts": {
                            **entry,
                            "nodes": [graph_node("src/evil.ts")],
                            "rawEdges": [],
                        }
                    }
                },
                {
                    "files": {
                        "src/a.ts": {
                            **entry,
                            "nodes": [graph_node("src/a.ts", span="../x:L1-L2")],
                            "rawEdges": [],
                        }
                    }
                },
                {
                    "files": {
                        "src/a.ts": {
                            **entry,
                            "nodes": [],
                            "rawEdges": [
                                {
                                    "source": "../../etc/passwd:L1-L2",
                                    "relation": "contains",
                                    "file": "src/a.ts",
                                }
                            ],
                        }
                    }
                },
                {
                    "files": {
                        "src/a.ts": {
                            **entry,
                            "nodes": [],
                            "rawEdges": [
                                {
                                    "source": "s",
                                    "relation": "imports",
                                    "file": "src/a.ts",
                                    "specifier": "../../etc/passwd:L1-L2",
                                }
                            ],
                        }
                    }
                },
            ]
            for payload in poisons:
                with self.subTest(payload=payload):
                    cache.write_text(json.dumps(payload))
                    self.assert_refused_readonly(
                        base, lambda: validate_build_scope(root)
                    )
            cache.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "extractor": "0123456789abcdef",
                        "files": {
                            "src/a.ts": {
                                **entry,
                                "nodes": [graph_node("src/a.ts")],
                                "rawEdges": [
                                    {
                                        "source": "src/a.ts",
                                        "relation": "imports",
                                        "file": "src/a.ts",
                                        "specifier": "lodash",
                                    }
                                ],
                            },
                            "src/broken.ts": {
                                **entry,
                                "nodes": [],
                                "rawEdges": [],
                                "error": "parse failed",
                            },
                        },
                    }
                )
            )
            self.assertIsNone(validate_build_scope(root))

    def test_poisoned_concept_pointers_refused_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            (root / "src").mkdir()
            (root / "src/a.ts").write_text("export const a = 1;\n")
            concept = root / "graft/Concept.md"
            poisons = [
                "---\nslug: Concept\nsources:\n  - path: ../../etc/passwd:L1-L2\n---\nbody\n",
                "---\nslug: ../../etc/passwd:L1-L2\n---\nbody\n",
                '---json\n{"slug": "../../etc/passwd:L1-L2"}\n---\nbody\n',
                "---javascript\n({slug: 'Concept'})\n---\nbody\n",
            ]
            for payload in poisons:
                with self.subTest(payload=payload):
                    concept.write_text(payload)
                    self.assert_refused_readonly(
                        base, lambda: validate_build_scope(root)
                    )
            concept.write_text(
                "---\nslug: Concept\nsources:\n  - path: src/a.ts\n    span: L1-L3\n---\nbody\n"
            )
            (root / "graft/INDEX.md").write_text(
                "---\nslug: ../../etc/passwd:L1-L2\n---\n# roster\n"
            )
            self.assertIsNone(validate_build_scope(root))

    def test_effective_concept_pointer_coercion_join_and_fallback_are_contained(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            victim = base / "private.txt"
            victim.write_bytes(b"private original\n")
            (root / "outside").symlink_to(victim)
            (root / "a, b").symlink_to(victim)
            cases = [
                ("concept.md", {"slug": ["../private.txt:L1-L2"]}),
                (
                    "concept.md",
                    {"slug": "safe", "sources": [{"path": ["../private.txt:L1-L2"]}]},
                ),
                (
                    "concept.md",
                    {"slug": "safe", "sources": [{"path": "outside:L1-L2"}]},
                ),
                ("outside:L1-L2.md", {"name": "fallback"}),
                ("concept.md", {"sources": [{"path": "a"}, {"path": "b:L1-L2"}]}),
            ]
            for filename, frontmatter in cases:
                with self.subTest(filename=filename, frontmatter=frontmatter):
                    concept = root / "graft" / filename
                    concept.write_text(
                        "---json\n" + json.dumps(frontmatter) + "\n---\nNeedle\n"
                    )
                    self.assert_refused_readonly(
                        base, lambda: validate_build_scope(root)
                    )
                    self.assertEqual(victim.read_bytes(), b"private original\n")
                    concept.unlink()

    def test_poisoned_manifest_probe_refused_readonly(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory).resolve()
            root = project_fixture(base)
            (root / "src").mkdir()
            (root / "src/a.ts").write_text("export const a = 1;\n")
            manifest = root / "graft/manifest.json"
            manifest.write_text(json.dumps({"files": [{"path": "../../etc/passwd"}]}))
            self.assert_refused_readonly(base, lambda: validate_build_scope(root))
            manifest.write_text(json.dumps({"files": [{"path": "src/a.ts"}]}))
            self.assertIsNone(validate_build_scope(root))


if __name__ == "__main__":
    unittest.main()
