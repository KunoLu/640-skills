"""Project language detection and omp LSP / ast-grep readiness (v2.2.0-rc.1).

Read-only detection plus consent-gated configuration writes for the omp
host's language tooling:

- ``detect_project_languages(root)`` reports which languages a project
  uses, from marker files and a bounded source-extension scan. The
  detection table is extensible: each language is a list of alternative
  clauses, and a clause matches when all its marker files exist at the
  project root and its source extension (if any) is found in the tree.
- ``check_language_tooling(roots)`` reports, per detected language,
  whether an omp built-in language server command is actually on PATH,
  whether a language without an omp built-in server (for example Julia)
  is covered by a custom ``~/.omp/agent/lsp.yml`` entry, and whether
  ``~/.omp/agent/config.yml`` has ``astGrep.enabled`` set.
- ``apply_language_tooling(report, confirmed=...)`` performs only the
  configuration writes (enable ``astGrep``, add custom ``lsp.yml``
  entries). Without ``confirmed=True`` it writes nothing and returns the
  guidance plus the impact of skipping. Language server binaries
  themselves are never installed here; the guidance lists their install
  commands for the operator to run explicitly.

Known omp facts baked into the guidance: omp resolves project roots from
its launch directory, so starting it in a parent directory leaves
Rust/TypeScript/Go projects in subdirectories without a language server;
and pyright only recognizes a Git repository without ``pyproject.toml``
when the global ``lsp.yml`` adds ``.git`` to its ``rootMarkers``.
"""

from __future__ import annotations

import os
import shutil
import stat
import tempfile
from pathlib import Path

import yaml

# Directories never entered by the bounded source scan.
_SCAN_SKIP_DIRS = frozenset(
    {
        ".git",
        ".graft",
        ".sbtd",
        ".trail",
        ".venv",
        "__pycache__",
        "build",
        "dist",
        "node_modules",
        "venv",
        "vendor",
    }
)
_SCAN_ENTRY_CAP = 5000

# Extensible detection table. Each language is a list of alternative
# clauses; a clause matches when every marker exists at the root and its
# extension (when given) is found by the bounded scan. ``servers`` lists
# omp built-in server commands for the language; an empty tuple means omp
# has no built-in server and a custom lsp.yml entry is required.
LANGUAGE_SPECS: tuple[dict[str, object], ...] = (
    {
        "language": "python",
        "display": "Python",
        "clauses": ({"markers": ("pyproject.toml",)}, {"extensions": (".py",)}),
        "extensions": (".py", ".pyi"),
        "servers": (
            {
                "command": "pyright",
                "install": "npm install -g pyright",
            },
        ),
        "notes": (
            "A Git repository without pyproject.toml needs the global "
            "~/.omp/agent/lsp.yml to add .git to pyright's rootMarkers, or "
            "omp does not treat it as a Python project root.",
        ),
    },
    {
        "language": "rust",
        "display": "Rust",
        "clauses": ({"markers": ("Cargo.toml",), "extensions": (".rs",)},),
        "extensions": (".rs",),
        "servers": (
            {
                "command": "rust-analyzer",
                "install": "rustup component add rust-analyzer",
            },
        ),
        "notes": (),
    },
    {
        "language": "typescript",
        "display": "TypeScript",
        "clauses": (
            {"markers": ("package.json", "tsconfig.json"), "extensions": (".ts",)},
        ),
        "extensions": (".ts", ".tsx"),
        "servers": (
            {
                "command": "typescript-language-server",
                "install": "npm install -g typescript-language-server typescript",
            },
        ),
        "notes": (),
    },
    {
        "language": "go",
        "display": "Go",
        "clauses": ({"markers": ("go.mod",), "extensions": (".go",)},),
        "extensions": (".go",),
        "servers": (
            {
                "command": "gopls",
                "install": "go install golang.org/x/tools/gopls@latest",
            },
        ),
        "notes": (),
    },
    {
        "language": "julia",
        "display": "Julia",
        "clauses": ({"extensions": (".jl",)},),
        "extensions": (".jl",),
        "servers": (),
        "customServer": {
            "name": "julia-languageserver",
            "entry": {
                "command": "julia",
                "args": [
                    "--startup-file=no",
                    "--history-file=no",
                    "-e",
                    "using LanguageServer; runserver()",
                ],
                "fileTypes": [".jl"],
                "languageId": "julia",
                "rootMarkers": ["Project.toml", "JuliaProject.toml", ".git"],
            },
            "install": "julia -e 'import Pkg; Pkg.add(\"LanguageServer\")'",
        },
        "notes": (
            "omp has no built-in Julia server; a custom entry in the global "
            "~/.omp/agent/lsp.yml is required.",
        ),
    },
)

_OMP_CONFIG_PARTS = (".omp", "agent", "config.yml")
_OMP_LSP_PARTS = (".omp", "agent", "lsp.yml")


def _scan_extensions(root: Path, wanted: frozenset[str]) -> set[str]:
    """Bounded scan for source extensions under root; never follows links."""
    found: set[str] = set()
    visited = 0
    stack = [root]
    while stack and visited < _SCAN_ENTRY_CAP and found != wanted:
        try:
            with os.scandir(stack.pop()) as entries:
                for entry in entries:
                    visited += 1
                    if visited > _SCAN_ENTRY_CAP:
                        break
                    if entry.is_dir(follow_symlinks=False):
                        if entry.name not in _SCAN_SKIP_DIRS:
                            stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        suffix = os.path.splitext(entry.name)[1]
                        if suffix in wanted:
                            found.add(suffix)
        except OSError:
            continue
    return found


def detect_project_languages(root: Path) -> list[dict[str, object]]:
    """Languages detected at a project root, with the matching evidence."""
    root = Path(root)
    detected: list[dict[str, object]] = []
    if not root.is_dir():
        return detected
    all_extensions = frozenset(
        extension
        for spec in LANGUAGE_SPECS
        for extension in spec["extensions"]  # type: ignore[index]
    )
    found_extensions = _scan_extensions(root, all_extensions)
    for spec in LANGUAGE_SPECS:
        for clause in spec["clauses"]:  # type: ignore[index]
            markers = tuple(clause.get("markers", ()))
            present = [name for name in markers if (root / name).is_file()]
            if len(present) != len(markers):
                continue
            extensions = tuple(clause.get("extensions", ()))
            matched_extensions = [ext for ext in extensions if ext in found_extensions]
            if extensions and not matched_extensions:
                continue
            detected.append(
                {
                    "language": spec["language"],
                    "display": spec["display"],
                    "markers": present,
                    "extensions": matched_extensions,
                    "builtIn": bool(spec["servers"]),
                }
            )
            break
    return detected


def _omp_config_path(home: Path) -> Path:
    return home.joinpath(*_OMP_CONFIG_PARTS)


def _omp_lsp_path(home: Path) -> Path:
    return home.joinpath(*_OMP_LSP_PARTS)


def _load_yaml_object(path: Path) -> tuple[dict[str, object], str | None]:
    """(mapping, None) for a YAML mapping; ({}, reason) otherwise."""
    try:
        raw = path.read_bytes()
    except FileNotFoundError:
        return {}, "absent"
    except OSError:
        return {}, "unreadable"
    try:
        data = yaml.safe_load(raw.decode("utf-8"))
    except (yaml.YAMLError, UnicodeDecodeError):
        return {}, "malformed"
    if data is None:
        return {}, "absent" if not raw.strip() else "malformed"
    if not isinstance(data, dict):
        return {}, "malformed"
    return data, None


def _ast_grep_status(home: Path) -> dict[str, object]:
    path = _omp_config_path(home)
    data, problem = _load_yaml_object(path)
    if problem == "malformed":
        return {"status": "unreadable", "path": str(path)}
    section = data.get("astGrep") if not problem else None
    if isinstance(section, dict) and "enabled" in section:
        return {
            "status": "enabled" if section["enabled"] is True else "disabled",
            "path": str(path),
        }
    return {"status": "not-configured", "path": str(path)}


def _custom_lsp_coverage(home: Path) -> dict[str, list[str]]:
    """Extensions covered by server entries in the global lsp.yml."""
    path = _omp_lsp_path(home)
    data, problem = _load_yaml_object(path)
    covered: dict[str, list[str]] = {}
    if problem:
        return covered
    servers = data.get("servers")
    if not isinstance(servers, dict):
        return covered
    for name, entry in servers.items():
        if not isinstance(entry, dict) or entry.get("disabled") is True:
            continue
        file_types = entry.get("fileTypes")
        if not isinstance(file_types, list):
            continue
        for file_type in file_types:
            if isinstance(file_type, str) and file_type.startswith("."):
                covered.setdefault(file_type, []).append(str(name))
    return covered


def check_language_tooling(
    project_roots: list[Path], *, home: Path | None = None
) -> dict[str, object]:
    """Read-only omp LSP / ast-grep readiness for the selected projects."""
    home = Path(home) if home is not None else Path.home()
    projects = [
        {"root": str(root), "languages": detect_project_languages(root)}
        for root in project_roots
    ]
    detected = {
        language["language"]
        for project in projects
        for language in project["languages"]  # type: ignore[index]
    }
    path_env = os.environ.get("PATH")
    languages: dict[str, object] = {}
    for spec in LANGUAGE_SPECS:
        name = str(spec["language"])
        if name not in detected:
            continue
        servers = []
        for server in spec["servers"]:  # type: ignore[index]
            binary = shutil.which(str(server["command"]), path=path_env)
            servers.append(
                {
                    "command": server["command"],
                    "install": server["install"],
                    "available": binary is not None,
                    "path": binary,
                }
            )
        entry: dict[str, object] = {
            "display": spec["display"],
            "builtIn": bool(servers),
            "servers": servers,
            "notes": list(spec["notes"]),  # type: ignore[index]
        }
        if servers:
            entry["ready"] = any(server["available"] for server in servers)
        else:
            coverage = _custom_lsp_coverage(home)
            covered = [
                extension
                for extension in spec["extensions"]  # type: ignore[index]
                if extension in coverage
            ]
            entry["customConfigured"] = bool(covered)
            entry["customServer"] = spec.get("customServer")
            entry["ready"] = bool(covered)
        languages[name] = entry
    ast_grep = _ast_grep_status(home)
    pending_writes: list[dict[str, object]] = []
    if detected and ast_grep["status"] != "enabled":
        pending_writes.append(
            {
                "action": "enable-ast-grep",
                "path": ast_grep["path"],
                "consentRequired": True,
            }
        )
    guidance: list[dict[str, object]] = []
    for name, entry in languages.items():
        if entry["builtIn"]:
            missing = [
                server for server in entry["servers"]  # type: ignore[index]
                if not server["available"]
            ]
            if not entry["ready"]:
                guidance.append(
                    {
                        "id": f"install-server-{name}",
                        "summary": (
                            f"{entry['display']} was detected but no omp "
                            "language server for it is on PATH."
                        ),
                        "steps": [
                            f"Install a server, for example: {server['install']}"
                            for server in missing
                        ],
                        "requiresConsent": False,
                        "skipImpact": (
                            f"omp provides no LSP navigation, diagnostics or "
                            f"rename for {entry['display']} files."
                        ),
                    }
                )
        elif not entry["customConfigured"]:
            custom = entry["customServer"]
            pending_writes.append(
                {
                    "action": "add-lsp-server",
                    "path": str(_omp_lsp_path(home)),
                    "server": custom["name"],  # type: ignore[index]
                    "entry": custom["entry"],  # type: ignore[index]
                    "consentRequired": True,
                }
            )
            guidance.append(
                {
                    "id": f"custom-server-{name}",
                    "summary": (
                        f"{entry['display']} was detected; omp has no built-in "
                        "server for it, so a custom lsp.yml entry is required."
                    ),
                    "steps": [
                        f"Install the server itself: {custom['install']}",  # type: ignore[index]
                        "Consent to the pending lsp.yml write to register the "
                        "custom server entry shown in pendingWrites.",
                    ],
                    "requiresConsent": True,
                    "skipImpact": (
                        f"omp cannot attach any language server to "
                        f"{entry['display']} files without the custom entry."
                    ),
                }
            )
    if detected and ast_grep["status"] != "enabled":
        guidance.append(
            {
                "id": "enable-ast-grep",
                "summary": "omp ast-grep search is not enabled.",
                "steps": [
                    "Consent to the pending config.yml write to set "
                    "astGrep.enabled: true."
                ],
                "requiresConsent": True,
                "skipImpact": "omp structural search/replace via ast-grep stays unavailable.",
            }
        )
    if not detected:
        status = "skipped"
    elif pending_writes or guidance:
        status = "action-required"
    else:
        status = "ready"
    return {
        "status": status,
        "projects": projects,
        "languages": languages,
        "astGrep": ast_grep,
        "pendingWrites": pending_writes,
        "guidance": guidance,
    }


def _atomic_replace(path: Path, content: bytes, *, backup: bool) -> Path | None:
    """Same-directory atomic replace; returns the backup path when made."""
    backup_path: Path | None = None
    if backup and path.exists():
        backup_path = path.with_name(path.name + ".sbtd-backup")
        backup_path.write_bytes(path.read_bytes())
        os.chmod(backup_path, stat.S_IRUSR | stat.S_IWUSR)
    handle, temp_name = tempfile.mkstemp(
        dir=str(path.parent), prefix=path.name + ".", suffix=".tmp"
    )
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(content)
        os.chmod(temp_name, stat.S_IRUSR | stat.S_IWUSR)
        os.replace(temp_name, path)
    except BaseException:
        try:
            os.unlink(temp_name)
        except OSError:
            pass
        raise
    return backup_path


def _enable_ast_grep(path: Path) -> None:
    """Minimal textual edit setting astGrep.enabled: true, verified after."""
    original = b""
    if path.exists():
        original = path.read_bytes()
        text = original.decode("utf-8")
        lines = text.splitlines()
        updated: list[str] = []
        in_section = False
        section_seen = False
        enabled_written = False
        for line in lines:
            stripped = line.strip()
            top_level = line[:1] not in {" ", "\t"} and stripped
            if top_level:
                if stripped == "astGrep:" or stripped.startswith("astGrep: "):
                    # Block or flow-style section header; an inline value only
                    # ever carries `enabled`, which is being set below.
                    in_section = True
                    section_seen = True
                    updated.append("astGrep:")
                    continue
                if in_section and not enabled_written:
                    updated.append("  enabled: true")
                    enabled_written = True
                in_section = False
            elif in_section and stripped.startswith("enabled:"):
                indent = line[: len(line) - len(line.lstrip())]
                updated.append(f"{indent}enabled: true")
                enabled_written = True
                continue
            updated.append(line)
        if in_section and not enabled_written:
            updated.append("  enabled: true")
        if not section_seen:
            if updated and updated[-1].strip():
                updated.append("")
            updated.extend(["astGrep:", "  enabled: true"])
        content = ("\n".join(updated) + "\n").encode("utf-8")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = b"astGrep:\n  enabled: true\n"
    try:
        parsed = yaml.safe_load(content.decode("utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"the astGrep enablement edit produced invalid YAML: {error}")
    if not isinstance(parsed, dict) or parsed.get("astGrep", {}).get("enabled") is not True:
        raise ValueError("the astGrep enablement edit did not produce the target state")
    if original:
        try:
            before = yaml.safe_load(original.decode("utf-8"))
        except yaml.YAMLError as error:
            raise ValueError(
                f"the existing config.yml is not readable YAML; refusing to edit: {error}"
            )
        if isinstance(before, dict) and not set(before).issubset(set(parsed)):
            raise ValueError("the astGrep enablement edit dropped top-level keys")
    _atomic_replace(path, content, backup=bool(original))

def _render_server_entry(name: str, entry: dict[str, object], indent: str) -> list[str]:
    lines = [f"{indent}{name}:"]
    body = yaml.safe_dump(
        entry, default_flow_style=False, sort_keys=False, allow_unicode=True
    ).splitlines()
    lines.extend(f"{indent}  {line}" for line in body)
    return lines


def _add_lsp_server(path: Path, name: str, entry: dict[str, object]) -> None:
    """Append one custom server to the global lsp.yml, verified after."""
    original = b""
    if path.exists():
        original = path.read_bytes()
        data, problem = _load_yaml_object(path)
        if problem == "malformed":
            raise ValueError("the existing lsp.yml is not a readable YAML mapping")
        servers = data.get("servers")
        if isinstance(servers, dict) and name in servers:
            return
        text = original.decode("utf-8")
        lines = text.splitlines()
        servers_line = next(
            (
                index
                for index, line in enumerate(lines)
                if line[:1] not in {" ", "\t"} and line.strip() == "servers:"
            ),
            None,
        )
        if servers_line is None:
            if lines and lines[-1].strip():
                lines.append("")
            lines.append("servers:")
            lines.extend(_render_server_entry(name, entry, "  "))
        else:
            child_indent = "  "
            for following in lines[servers_line + 1 :]:
                if not following.strip():
                    continue
                if following[:1] not in {" ", "\t"}:
                    break
                child_indent = following[: len(following) - len(following.lstrip())]
                break
            lines[servers_line + 1 : servers_line + 1] = _render_server_entry(
                name, entry, child_indent
            )
        content = ("\n".join(lines) + "\n").encode("utf-8")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        content = (
            "servers:\n" + "\n".join(_render_server_entry(name, entry, "  ")) + "\n"
        ).encode("utf-8")
    try:
        parsed = yaml.safe_load(content.decode("utf-8"))
    except yaml.YAMLError as error:
        raise ValueError(f"the lsp.yml edit produced invalid YAML: {error}")
    servers = parsed.get("servers") if isinstance(parsed, dict) else None
    if not isinstance(servers, dict) or servers.get(name) != entry:
        raise ValueError("the lsp.yml edit did not produce the target server entry")
    if original:
        before = yaml.safe_load(original.decode("utf-8"))
        before_servers = before.get("servers") if isinstance(before, dict) else None
        if isinstance(before_servers, dict) and not set(before_servers).issubset(servers):
            raise ValueError("the lsp.yml edit dropped existing server entries")
    _atomic_replace(path, content, backup=bool(original))


def apply_language_tooling(
    report: dict[str, object], *, confirmed: bool, home: Path | None = None
) -> dict[str, object]:
    """Consent-gated application of the pending configuration writes.

    ``confirmed=False`` performs zero writes and returns the plan with the
    impact of skipping; ``confirmed=True`` applies each pending write and
    re-verifies the resulting state.
    """
    pending = list(report.get("pendingWrites", ()))  # type: ignore[arg-type]
    guidance = list(report.get("guidance", ()))  # type: ignore[arg-type]
    if not pending:
        return {**report, "status": report.get("status", "ready"), "writes": []}
    if not confirmed:
        return {
            **report,
            "status": "needs-confirmation",
            "writes": [],
            "skippedImpact": [
                item["skipImpact"] for item in guidance if item.get("requiresConsent")
            ],
            "nextStep": (
                "Rerun the workflow mode with --language-tooling after "
                "confirmation to apply the pending omp config writes."
            ),
        }
    writes: list[dict[str, object]] = []
    failures: list[dict[str, object]] = []
    for write in pending:
        path = Path(str(write["path"]))
        try:
            if write["action"] == "enable-ast-grep":
                _enable_ast_grep(path)
            elif write["action"] == "add-lsp-server":
                _add_lsp_server(
                    path,
                    str(write["server"]),
                    dict(write["entry"]),  # type: ignore[arg-type]
                )
            else:
                raise ValueError(f"unknown language tooling write: {write['action']}")
        except (OSError, ValueError) as error:
            failures.append({"path": str(path), "action": write["action"], "error": str(error)})
        else:
            writes.append({"path": str(path), "action": write["action"]})
    if failures:
        return {
            **report,
            "status": "failed",
            "writes": writes,
            "failures": failures,
            "nextStep": "Inspect the reported paths; completed writes are kept.",
        }
    home_path = Path(home) if home is not None else Path.home()
    recheck = _ast_grep_status(home_path)
    return {
        **report,
        "status": "configured",
        "writes": writes,
        "astGrep": recheck,
        "nextStep": (
            "Install any language server binaries listed in guidance; omp "
            "configuration writes are complete."
        ),
    }
