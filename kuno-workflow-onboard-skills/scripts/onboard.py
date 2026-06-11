#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import filecmp
import json
import os
import platform
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path


SKILL_DIR = Path(__file__).resolve().parents[1]
TEMPLATE_DIR = SKILL_DIR / "templates"
PROJECT_GITIGNORE_TEMPLATE = TEMPLATE_DIR / "project" / ".gitignore"
NVM_INSTALL_URL = "https://raw.githubusercontent.com/nvm-sh/nvm/v0.40.5/install.sh"
RTK_INSTALL_URL = "https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh"
SKILL_SOURCES = {
    "kuno-workflow-onboard-skills": SKILL_DIR,
    "trellis-workflow": TEMPLATE_DIR / "skills" / "trellis-workflow",
    "trellis-channel": TEMPLATE_DIR / "skills" / "trellis-channel",
    "project-validation": TEMPLATE_DIR / "skills" / "project-validation",
    "lessons-record": TEMPLATE_DIR / "skills" / "lessons-record",
}
CLI_TOOLS = (
    {
        "name": "rtk",
        "versionArgs": ("--version",),
        "globalInstall": "curl -fsSL https://raw.githubusercontent.com/rtk-ai/rtk/refs/heads/master/install.sh | sh",
        "projectInstall": None,
        "advice": "Install RTK from rtk-ai/rtk and verify with `rtk gain`; do not treat the unrelated Rust Type Kit package as valid.",
    },
    {
        "name": "trellis",
        "versionArgs": ("--version",),
        "globalInstall": "npm install -g @mindfoldhq/trellis",
        "projectInstall": "npm install -D @mindfoldhq/trellis",
        "advice": "Install Trellis globally for cross-project workflow use, or as a project dev dependency and run it through npx.",
    },
    {
        "name": "gitnexus",
        "versionArgs": ("--version",),
        "globalInstall": "npm install -g gitnexus",
        "projectInstall": "npm install -D gitnexus",
        "advice": "Install GitNexus globally when sharing the MCP/CLI across projects, or as a project dev dependency for project-local usage.",
    },
)
BUNDLED_SKILLS = tuple(SKILL_SOURCES.keys())
REFERENCED_SKILLS = (
    "diagnose",
    "tdd",
    "grill-me",
    "grill-with-docs",
    "handoff",
    "write-a-skill",
    "zoom-out",
    "to-prd",
    "to-issues",
    "ui-ux-pro-max",
    "impeccable",
    "web-ui-autotest-generator",
)
MATTPOCOCK_SKILLS = (
    "diagnose",
    "tdd",
    "grill-me",
    "grill-with-docs",
    "handoff",
    "write-a-skill",
    "zoom-out",
    "to-prd",
    "to-issues",
)
MATTPOCOCK_REPO = "https://github.com/mattpocock/skills.git"
EXTERNAL_SKILL_SOURCES = {
    **{
        name: {
            "repo": MATTPOCOCK_REPO,
            "aliases": (name,),
        }
        for name in MATTPOCOCK_SKILLS
    },
    "impeccable": {
        "repo": "https://github.com/pbakaus/impeccable.git",
        "aliases": ("impeccable",),
    },
    "ui-ux-pro-max": {
        "repo": "https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git",
        "aliases": ("ui-ux-pro-max", "ui-ux-pro-max-skill"),
    },
    "web-ui-autotest-generator": {
        "repo": "https://github.com/Cheryl-station/web-ui-autotest.git",
        "aliases": ("web-ui-autotest-generator", "web-ui-autotest"),
    },
}
EXTERNAL_REPO_TO_SKILLS: dict[str, tuple[str, ...]] = {}
for _skill_name, _source_spec in EXTERNAL_SKILL_SOURCES.items():
    _repo = str(_source_spec["repo"])
    EXTERNAL_REPO_TO_SKILLS[_repo] = (*EXTERNAL_REPO_TO_SKILLS.get(_repo, ()), _skill_name)
MANUAL_CHECKS = (
    {
        "name": "GitNexus MCP",
        "category": "mcp",
        "advice": "After GitNexus CLI is installed, confirm the current Agent environment exposes GitNexus MCP tools and that the target project has an index before relying on GitNexus analysis.",
        "steps": (
            "Confirm the GitNexus CLI works, for example with `npx gitnexus status` in the target project.",
            "Configure or enable the GitNexus MCP server in the active Agent or IDE MCP settings using the current GitNexus setup instructions.",
            "Restart or reload the Agent environment so the MCP server is discovered.",
            "Confirm GitNexus MCP tools or resources are visible to the Agent, then check the target project index.",
            "If the project is not indexed yet, run GitNexus analysis from the project root and re-check MCP visibility.",
        ),
    },
    {
        "name": "TestSprite MCP",
        "category": "mcp",
        "advice": "Confirm the IDE/Agent MCP configuration and API key. TestSprite setup may require its local configuration portal and should not be treated as a background-only install.",
        "steps": (
            "Add or enable the TestSprite MCP server in the active IDE or Agent MCP configuration.",
            "Provide the TestSprite API key or local auth through a secret store, environment variable, or MCP config; do not write secrets into the repository.",
            "Run the TestSprite bootstrap/check command from the Agent environment.",
            "Complete any TestSprite configuration portal fields, including project path, local URL or port, app type, test scope, PRD upload, and non-sensitive test account details when required.",
            "Rerun the MCP check and only treat TestSprite as usable after the MCP tools and target test environment are reachable.",
        ),
    },
    {
        "name": "React Bits Pro Skill",
        "category": "conditional-project-skill",
        "advice": "Only install in React/shadcn projects with registry configuration and REACTBITS_LICENSE_KEY available. Do not print or store the license key.",
        "steps": (
            "Confirm the target project is a React project with shadcn/ui initialized and `components.json` present.",
            "Confirm `components.json` contains the required React Bits registry entries and the current environment can read `REACTBITS_LICENSE_KEY` without printing it.",
            "If prerequisites are met but the project Skill is missing, run `npx shadcn@latest add @reactbits-starter/skill` from the project root.",
            "Confirm the React Bits Pro `SKILL.md` exists in the project and rerun the onboard check.",
            "Skip this item for non-React projects, projects without a license key, or projects that do not need React Bits Pro.",
        ),
    },
)


@dataclass(frozen=True)
class Operation:
    label: str
    source: Path
    target: Path
    kind: str
    same_location: bool = False


def expand_path(value: str | None) -> Path | None:
    if not value:
        return None
    return Path(value).expanduser().resolve()


def default_codex_home() -> Path:
    env_value = os.environ.get("CODEX_HOME")
    if env_value:
        return Path(env_value).expanduser().resolve()
    return (Path.home() / ".codex").resolve()


def default_global_skills_dir() -> Path:
    skills_dir = os.environ.get("AGENT_SKILLS_DIR")
    if skills_dir:
        return Path(skills_dir).expanduser().resolve()
    if platform.system() == "Windows":
        user_profile = os.environ.get("USERPROFILE")
        home = Path(user_profile).expanduser() if user_profile else Path.home()
        return (home / ".codex" / "skills").resolve()
    return (Path.home() / ".codex" / "skills").resolve()


def resolve_project_root(args: argparse.Namespace, required: bool = False) -> Path | None:
    project_root = expand_path(getattr(args, "project_root", None))
    if project_root and not project_root.is_dir():
        raise SystemExit(f"--project-root must be an existing directory: {project_root}")
    if required and not project_root:
        raise SystemExit("--project-root is required unless --skip-project-agents is used")
    return project_root


def resolve_project_skills_dir(args: argparse.Namespace, project_root: Path | None) -> Path | None:
    explicit = expand_path(getattr(args, "project_skills_dir", None))
    if explicit:
        return explicit
    if project_root:
        return project_root / ".agent" / "skills"
    return None


def run_command(command: tuple[str, ...], timeout: int = 30, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str] | None:
    try:
        return subprocess.run(
            command,
            check=False,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None


def shell_result(script: str, timeout: int = 300) -> subprocess.CompletedProcess[str] | None:
    shell = shutil.which("bash") or shutil.which("sh")
    if not shell:
        return None
    return run_command((shell, "-lc", script), timeout=timeout)


def command_output(command: tuple[str, ...], timeout: int = 10, env: dict[str, str] | None = None) -> tuple[int | None, str]:
    completed = run_command(command, timeout=timeout, env=env)
    if completed is None:
        return None, ""
    output = (completed.stdout or completed.stderr).strip()
    return completed.returncode, output


def command_version(command: str, version_args: tuple[str, ...]) -> str | None:
    _, output = command_output((command, *version_args), timeout=5)
    return output.splitlines()[0] if output else None


def nvm_dir_shell_expr() -> str:
    return '${NVM_DIR:-$([ -z "${XDG_CONFIG_HOME-}" ] && printf %s "$HOME/.nvm" || printf %s "$XDG_CONFIG_HOME/nvm")}'


def nvm_load_script() -> str:
    nvm_dir = nvm_dir_shell_expr()
    return f'export NVM_DIR="{nvm_dir}"; [ -s "$NVM_DIR/nvm.sh" ] && . "$NVM_DIR/nvm.sh"'


def check_nvm() -> dict[str, object]:
    system = platform.system() or sys.platform
    if system == "Windows":
        path = shutil.which("nvm")
        version = command_version("nvm", ("version",)) if path else None
        return {
            "name": "nvm",
            "installed": bool(path),
            "path": path,
            "version": version,
            "installableByScript": False,
            "advice": "Native Windows should use nvm-windows, nvs, or WSL; the nvm-sh installer is for POSIX shells.",
        }

    completed = shell_result(f'{nvm_load_script()}; command -v nvm; nvm --version', timeout=10)
    installed = bool(completed and completed.returncode == 0)
    lines = (completed.stdout if completed else "").strip().splitlines()
    return {
        "name": "nvm",
        "installed": installed,
        "path": lines[0] if lines else None,
        "version": lines[-1] if len(lines) > 1 else None,
        "installableByScript": system in {"Darwin", "Linux"},
        "advice": "Install nvm first, then use `nvm install --lts`, `nvm alias default 'lts/*'`, and `nvm use --lts`.",
    }


def activate_nvm_node_path() -> str | None:
    if platform.system() == "Windows":
        return None
    completed = shell_result(
        f"{nvm_load_script()}; "
        "(nvm use --lts >/dev/null 2>&1 || nvm use default >/dev/null 2>&1 || true); "
        "command -v npm",
        timeout=20,
    )
    if not completed or completed.returncode != 0:
        return None
    npm_path = completed.stdout.strip().splitlines()[-1] if completed.stdout.strip() else ""
    if not npm_path:
        return None
    npm_bin = str(Path(npm_path).parent)
    current = os.environ.get("PATH", "")
    if npm_bin not in current.split(os.pathsep):
        os.environ["PATH"] = f"{npm_bin}{os.pathsep}{current}"
    return npm_bin


def check_npm_runtime() -> dict[str, object]:
    if not shutil.which("npm"):
        activate_nvm_node_path()
    npm_path = shutil.which("npm")
    node_path = shutil.which("node")
    npm_version = command_version("npm", ("--version",)) if npm_path else None
    node_version = command_version("node", ("--version",)) if node_path else None
    nvm = check_nvm()
    return {
        "platform": platform.system() or sys.platform,
        "npm": {
            "installed": bool(npm_path and npm_version),
            "path": npm_path,
            "version": npm_version,
        },
        "node": {
            "installed": bool(node_path and node_version),
            "path": node_path,
            "version": node_version,
        },
        "nvm": nvm,
        "requiredBeforeCliChecks": True,
        "advice": "CLI tool checks run only after npm is usable. If npm is missing, run `python scripts/onboard.py ensure-npm --yes` after user confirmation.",
    }


def check_cli_tool(spec: dict[str, str | tuple[str, ...]]) -> dict[str, object]:
    name = str(spec["name"])
    path = shutil.which(name)
    version = command_version(name, spec["versionArgs"]) if path else None
    installed = bool(path and version)
    result = {
        "name": name,
        "category": "cli",
        "installed": installed,
        "path": path,
        "version": version,
        "globalInstall": spec["globalInstall"],
        "projectInstall": spec["projectInstall"],
        "advice": spec["advice"],
    }
    if name == "rtk" and path:
        code, output = command_output(("rtk", "gain"), timeout=10)
        correct = code == 0
        version_looks_correct = bool(version and version.lower().startswith("rtk "))
        result["installed"] = correct
        result["rtkGainVerified"] = correct
        result["wrongPackageSuspected"] = not correct and not version_looks_correct
        result["verificationFailed"] = not correct and version_looks_correct
        result["verifyCommand"] = "rtk gain"
        result["verifyOutput"] = output.splitlines()[0] if output else None
        if result["wrongPackageSuspected"]:
            result["advice"] = "An `rtk` command exists but `rtk gain` failed, so this may be the wrong rtk package. Confirm before uninstalling or replacing it."
        elif result["verificationFailed"]:
            result["advice"] = "The rtk binary looks like rtk-ai/rtk, but `rtk gain` failed. Troubleshoot RTK data directory permissions or reinstall after user confirmation."
    elif name == "rtk":
        result["rtkGainVerified"] = False
        result["wrongPackageSuspected"] = False
        result["verificationFailed"] = False
        result["verifyCommand"] = "rtk gain"
    return result


def check_skill(name: str, group: str, global_dir: Path, project_dir: Path | None) -> dict[str, object]:
    locations: list[dict[str, str]] = []
    global_candidate = global_dir / name / "SKILL.md"
    if global_candidate.is_file():
        locations.append({"scope": "global", "path": str(global_candidate)})
    if project_dir:
        project_candidate = project_dir / name / "SKILL.md"
        if project_candidate.is_file():
            locations.append({"scope": "project", "path": str(project_candidate)})

    return {
        "name": name,
        "category": "skill",
        "group": group,
        "installed": bool(locations),
        "locations": locations,
        "globalTarget": str(global_dir / name / "SKILL.md"),
        "projectTarget": str(project_dir / name / "SKILL.md") if project_dir else None,
        "sourceRepo": EXTERNAL_SKILL_SOURCES.get(name, {}).get("repo") if group == "referenced" else None,
    }


def report_entry(
    name: str,
    status: str,
    *,
    path: str | None = None,
    version: str | None = None,
    scope: str | None = None,
    reason: str | None = None,
    next_step: str | None = None,
    source_repo: str | None = None,
) -> dict[str, object]:
    entry: dict[str, object] = {"name": name, "status": status}
    optional = {
        "path": path,
        "version": version,
        "scope": scope,
        "reason": reason,
        "nextStep": next_step,
        "sourceRepo": source_repo,
    }
    for key, value in optional.items():
        if value:
            entry[key] = value
    return entry


def cli_failure_reason(item: dict[str, object]) -> str:
    name = str(item["name"])
    if item.get("wrongPackageSuspected"):
        reason = f"`{name}` exists at {item.get('path')}, but `{item.get('verifyCommand')}` failed; it may be a different same-name package."
    elif item.get("verificationFailed"):
        reason = f"`{name}` exists at {item.get('path')}, but `{item.get('verifyCommand')}` failed."
    elif not item.get("path"):
        reason = f"`{name}` command was not found in PATH."
    elif not item.get("version"):
        reason = f"`{name}` exists at {item.get('path')}, but the version command returned no usable output."
    else:
        reason = f"`{name}` did not pass the installer verification checks."

    verify_output = item.get("verifyOutput")
    if verify_output:
        reason += f" First verification output: {verify_output}"
    return reason


def cli_next_step(item: dict[str, object]) -> str:
    commands = [f"global: {item['globalInstall']}"]
    if item.get("projectInstall"):
        commands.append(f"project: {item['projectInstall']}")
    return "Confirm the desired scope with the user, then install or repair it. Suggested command(s): " + "; ".join(commands)


def skill_failure_reason(item: dict[str, object]) -> str:
    targets = [str(item["globalTarget"])]
    if item.get("projectTarget"):
        targets.append(str(item["projectTarget"]))
    return "No `SKILL.md` was found at the checked target path(s): " + ", ".join(targets)


def skill_next_step(item: dict[str, object]) -> str:
    name = str(item["name"])
    if item.get("sourceRepo"):
        return (
            "After user confirmation, install from the configured repository with "
            f"`python scripts/onboard.py install-external-skills --skills {name} --scope global|project --yes`."
        )
    return "Run `init` or `reset` with the confirmed skills scope, then rerun `check`."


def skipped_already_installed_entry(
    entry: dict[str, object],
    reason: str,
    next_step: str,
) -> dict[str, object]:
    skipped = dict(entry)
    skipped["status"] = "skipped-already-installed"
    skipped["reason"] = reason
    skipped["nextStep"] = next_step
    return skipped


def build_installation_report(results: dict[str, object]) -> dict[str, object]:
    runtime = results["runtime"]
    installed: dict[str, list[dict[str, object]]] = {"runtime": [], "tools": [], "skills": []}
    skipped_already_installed: dict[str, list[dict[str, object]]] = {"runtime": [], "tools": [], "skills": []}
    failed_or_missing: dict[str, list[dict[str, object]]] = {"runtime": [], "tools": [], "skills": []}
    not_checked: dict[str, list[dict[str, object]]] = {"tools": []}

    for name in ("npm", "node"):
        item = runtime[name]
        entry = report_entry(
            name,
            "installed" if item["installed"] else "missing",
            path=item.get("path"),
            version=item.get("version"),
        )
        if item["installed"]:
            installed["runtime"].append(entry)
            skipped_already_installed["runtime"].append(
                skipped_already_installed_entry(
                    entry,
                    f"`{name}` is already available in PATH.",
                    "Skip bootstrap installation unless the user explicitly requests a reinstall or version change.",
                )
            )
        else:
            entry["reason"] = f"`{name}` is not available in PATH."
            entry["nextStep"] = runtime["advice"] if name == "npm" else "Install Node.js through nvm or the platform package manager, then rerun `check`."
            failed_or_missing["runtime"].append(entry)

    nvm = runtime["nvm"]
    nvm_entry = report_entry(
        "nvm",
        "installed" if nvm["installed"] else "missing",
        path=nvm.get("path"),
        version=nvm.get("version"),
    )
    if nvm["installed"]:
        installed["runtime"].append(nvm_entry)
        skipped_already_installed["runtime"].append(
            skipped_already_installed_entry(
                nvm_entry,
                "`nvm` is already available.",
                "Skip nvm bootstrap unless the user explicitly requests a reinstall or version manager change.",
            )
        )
    elif not runtime["npm"]["installed"]:
        nvm_entry["reason"] = "npm is missing and nvm is not available for bootstrap."
        nvm_entry["nextStep"] = nvm["advice"]
        failed_or_missing["runtime"].append(nvm_entry)

    if results["cliChecksSkipped"]:
        for spec in CLI_TOOLS:
            not_checked["tools"].append(
                report_entry(
                    str(spec["name"]),
                    "not-checked",
                    reason="npm is not usable yet, so CLI verification was skipped.",
                    next_step="Run `python scripts/onboard.py ensure-npm --yes` after user confirmation, then rerun `check`.",
                )
            )
    else:
        for item in results["tools"]:
            entry = report_entry(
                str(item["name"]),
                "installed" if item["installed"] else "missing",
                path=item.get("path"),
                version=item.get("version"),
            )
            if item["installed"]:
                installed["tools"].append(entry)
                skipped_already_installed["tools"].append(
                    skipped_already_installed_entry(
                        entry,
                        f"`{item['name']}` is already installed and passed the current verification checks.",
                        "Skip CLI installation unless the user explicitly requests reinstall, upgrade, replacement, or project-local installation.",
                    )
                )
            else:
                if item.get("wrongPackageSuspected"):
                    entry["status"] = "wrong-package-suspected"
                elif item.get("verificationFailed"):
                    entry["status"] = "verification-failed"
                entry["reason"] = cli_failure_reason(item)
                entry["nextStep"] = cli_next_step(item)
                failed_or_missing["tools"].append(entry)

    for item in results["skills"]:
        locations = item["locations"]
        if item["installed"]:
            for location in locations:
                installed["skills"].append(
                    report_entry(
                        str(item["name"]),
                        "installed",
                        path=location["path"],
                        scope=location["scope"],
                        source_repo=item.get("sourceRepo"),
                    )
                )
            continue

        failed_or_missing["skills"].append(
            report_entry(
                str(item["name"]),
                "missing",
                reason=skill_failure_reason(item),
                next_step=skill_next_step(item),
                source_repo=item.get("sourceRepo"),
            )
        )

    manual_configuration = [
        {
            "name": item["name"],
            "category": item["category"],
            "status": "manual-required",
            "reason": "This item cannot be proven or completed safely by the installer alone.",
            "advice": item["advice"],
            "steps": item["steps"],
        }
        for item in results["manualChecks"]
    ]

    installed_count = sum(len(items) for items in installed.values())
    skipped_count = sum(len(items) for items in skipped_already_installed.values())
    failed_count = sum(len(items) for items in failed_or_missing.values())
    not_checked_count = sum(len(items) for items in not_checked.values())
    return {
        "summary": {
            "installed": installed_count,
            "skippedAlreadyInstalled": skipped_count,
            "failedOrMissing": failed_count,
            "notChecked": not_checked_count,
            "manualConfiguration": len(manual_configuration),
        },
        "installed": installed,
        "skippedAlreadyInstalled": skipped_already_installed,
        "failedOrMissing": failed_or_missing,
        "notChecked": not_checked,
        "manualConfiguration": manual_configuration,
    }


def build_check_results(args: argparse.Namespace) -> dict[str, object]:
    project_root = resolve_project_root(args)
    global_skills_dir = expand_path(getattr(args, "global_skills_dir", None)) or default_global_skills_dir()
    project_skills_dir = resolve_project_skills_dir(args, project_root)
    runtime = check_npm_runtime()
    skills = [
        check_skill(name, "bundled", global_skills_dir, project_skills_dir)
        for name in BUNDLED_SKILLS
    ]
    skills.extend(
        check_skill(name, "referenced", global_skills_dir, project_skills_dir)
        for name in REFERENCED_SKILLS
    )

    cli_checks_skipped = not runtime["npm"]["installed"]
    tools = [] if cli_checks_skipped else [check_cli_tool(spec) for spec in CLI_TOOLS]
    missing = {
        "runtime": [] if runtime["npm"]["installed"] else ["npm"],
        "tools": [item["name"] for item in tools if not item["installed"]],
        "skills": [item["name"] for item in skills if not item["installed"]],
    }

    results = {
        "mode": "check",
        "platform": platform.system() or sys.platform,
        "paths": {
            "globalSkillsDir": str(global_skills_dir),
            "projectRoot": str(project_root) if project_root else None,
            "projectSkillsDir": str(project_skills_dir) if project_skills_dir else None,
        },
        "runtime": runtime,
        "cliChecksSkipped": cli_checks_skipped,
        "tools": tools,
        "skills": skills,
        "manualChecks": MANUAL_CHECKS,
        "missing": missing,
    }
    results["installationReport"] = build_installation_report(results)
    return results


def print_report_entries(entries: list[dict[str, object]], empty_message: str = "- none") -> None:
    if not entries:
        print(empty_message)
        return
    for item in entries:
        detail = []
        if item.get("scope"):
            detail.append(f"scope={item['scope']}")
        if item.get("path"):
            detail.append(f"path={item['path']}")
        if item.get("version"):
            detail.append(f"version={item['version']}")
        suffix = f" ({', '.join(detail)})" if detail else ""
        print(f"- {item['name']}: {item['status']}{suffix}")
        if item.get("sourceRepo"):
            print(f"  source repo: {item['sourceRepo']}")
        if item.get("reason"):
            print(f"  reason: {item['reason']}")
        if item.get("nextStep"):
            print(f"  next: {item['nextStep']}")


def print_installation_report(report: dict[str, object], heading: str = "Installation report") -> None:
    print(f"\n{heading}:")
    summary = report["summary"]
    print(
        "Summary: "
        f"installed={summary['installed']}, "
        f"skipped_already_installed={summary['skippedAlreadyInstalled']}, "
        f"failed_or_missing={summary['failedOrMissing']}, "
        f"not_checked={summary['notChecked']}, "
        f"manual_configuration={summary['manualConfiguration']}"
    )

    print("\nInstalled runtime:")
    print_report_entries(report["installed"]["runtime"])
    print("\nInstalled CLI tools:")
    print_report_entries(report["installed"]["tools"])
    print("\nInstalled skills:")
    print_report_entries(report["installed"]["skills"])

    print("\nSkipped because already installed - runtime:")
    print_report_entries(report["skippedAlreadyInstalled"]["runtime"])
    print("\nSkipped because already installed - CLI tools:")
    print_report_entries(report["skippedAlreadyInstalled"]["tools"])

    print("\nFailed or missing runtime:")
    print_report_entries(report["failedOrMissing"]["runtime"])
    print("\nFailed or missing CLI tools:")
    print_report_entries(report["failedOrMissing"]["tools"])
    print("\nFailed or missing skills:")
    print_report_entries(report["failedOrMissing"]["skills"])

    print("\nNot checked:")
    print_report_entries(report["notChecked"]["tools"])

    print("\nManual configuration required:")
    manual_items = report["manualConfiguration"]
    if not manual_items:
        print("- none")
    for item in manual_items:
        print(f"- {item['name']} [{item['category']}]: {item['status']}")
        print(f"  reason: {item['reason']}")
        print(f"  advice: {item['advice']}")
        print("  steps:")
        for index, step in enumerate(item["steps"], start=1):
            print(f"  {index}. {step}")


def print_check_results(results: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(results, indent=2, ensure_ascii=False))
        return

    print("Preflight check")
    print(f"Platform: {results['platform']}")
    paths = results["paths"]
    print(f"Global skills: {paths['globalSkillsDir']}")
    if paths["projectRoot"]:
        print(f"Project root: {paths['projectRoot']}")
        print(f"Project skills: {paths['projectSkillsDir']}")

    runtime = results["runtime"]
    print("\nRuntime preflight:")
    npm = runtime["npm"]
    node = runtime["node"]
    nvm = runtime["nvm"]
    npm_status = "installed" if npm["installed"] else "missing"
    node_status = "installed" if node["installed"] else "missing"
    nvm_status = "installed" if nvm["installed"] else "missing"
    print(f"- npm: {npm_status}" + (f" at {npm['path']} ({npm['version']})" if npm.get("path") else ""))
    print(f"- node: {node_status}" + (f" at {node['path']} ({node['version']})" if node.get("path") else ""))
    print(f"- nvm: {nvm_status}" + (f" ({nvm['version']})" if nvm.get("version") else ""))
    if not npm["installed"]:
        print("  action: ask the user to install npm via nvm, then run `python scripts/onboard.py ensure-npm --yes`.")

    print("\nCLI tools:")
    if results["cliChecksSkipped"]:
        print("- skipped: npm is not usable yet, so CLI tool checks have not run.")
    else:
        for item in results["tools"]:
            status = "installed" if item["installed"] else "missing"
            if item.get("wrongPackageSuspected"):
                status = "wrong-package-suspected"
            elif item.get("verificationFailed"):
                status = "verification-failed"
            detail = f" ({item['version']})" if item.get("version") else ""
            path = f" at {item['path']}" if item.get("path") else ""
            print(f"- {item['name']}: {status}{path}{detail}")
            if item.get("verifyCommand"):
                verified = "passed" if item.get("rtkGainVerified") else "not passed"
                print(f"  verify: {item['verifyCommand']} ({verified})")
            if not item["installed"]:
                print(f"  global: {item['globalInstall']}")
                if item.get("projectInstall"):
                    print(f"  project: {item['projectInstall']}")
                print(f"  advice: {item['advice']}")

    print("\nSkills:")
    for item in results["skills"]:
        status = "installed" if item["installed"] else "missing"
        print(f"- {item['name']} [{item['group']}]: {status}")
        for location in item["locations"]:
            print(f"  {location['scope']}: {location['path']}")
        if not item["installed"]:
            print(f"  global target: {item['globalTarget']}")
            if item["projectTarget"]:
                print(f"  project target: {item['projectTarget']}")
            if item.get("sourceRepo"):
                print(f"  source repo: {item['sourceRepo']}")

    print("\nManual checks:")
    for item in results["manualChecks"]:
        print(f"- {item['name']} [{item['category']}]: {item['advice']}")

    missing = results["missing"]
    if missing["runtime"] or missing["tools"] or missing["skills"]:
        print("\nMissing summary:")
        if missing["runtime"]:
            print("- runtime: " + ", ".join(missing["runtime"]))
        if missing["tools"]:
            print("- tools: " + ", ".join(missing["tools"]))
        if missing["skills"]:
            print("- skills: " + ", ".join(missing["skills"]))
        print("Ask the user whether to install missing items and confirm global vs project scope before init/reset.")
    else:
        print("\nMissing summary: none")

    print_installation_report(results["installationReport"])


def backup_path(target: Path) -> Path:
    today = dt.date.today().isoformat()
    index = 1
    while True:
        candidate = target.with_name(f"{target.name}.{today}-{index}")
        if not candidate.exists():
            return candidate
        index += 1


def compare_tree(source: Path, target: Path, ignored_names: set[str] | None = None) -> list[str]:
    failures: list[str] = []
    ignored = ignored_names or set()
    for item in source.rglob("*"):
        rel = item.relative_to(source)
        if any(part in ignored for part in rel.parts):
            continue
        if item.name.endswith(".pyc"):
            continue
        other = target / rel
        if item.is_dir():
            if not other.is_dir():
                failures.append(str(rel))
            continue
        if not other.is_file() or not filecmp.cmp(item, other, shallow=False):
            failures.append(str(rel))
    return failures


def ensure_file_contains(source: Path, target: Path) -> str:
    source_text = source.read_text(encoding="utf-8")
    if not source_text.endswith("\n"):
        source_text += "\n"

    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.write_text(source_text, encoding="utf-8")
        return "created"

    existing = target.read_text(encoding="utf-8")
    if source_text.strip() in existing:
        return "skipped-already-present"

    prefix = "" if not existing or existing.endswith("\n") else "\n"
    separator = "\n" if existing.strip() else ""
    target.write_text(f"{existing}{prefix}{separator}{source_text}", encoding="utf-8")
    return "updated"


def copy_operation(operation: Operation) -> str:
    if operation.same_location:
        return "skipped-same-location"
    operation.target.parent.mkdir(parents=True, exist_ok=True)
    if operation.kind == "ensure-file-block":
        return ensure_file_contains(operation.source, operation.target)
    if operation.kind == "file":
        shutil.copy2(operation.source, operation.target)
        return "copied"
    shutil.copytree(operation.source, operation.target)
    return "copied"


def verify_operation(operation: Operation) -> list[str]:
    if operation.same_location:
        return []
    if operation.kind == "ensure-file-block":
        if not operation.target.is_file():
            return [operation.label]
        source_text = operation.source.read_text(encoding="utf-8").strip()
        target_text = operation.target.read_text(encoding="utf-8")
        if source_text and source_text in target_text:
            return []
        return [operation.label]
    if operation.kind == "file":
        if operation.target.is_file() and filecmp.cmp(operation.source, operation.target, shallow=False):
            return []
        return [operation.label]
    return compare_tree(operation.source, operation.target)


def parse_skill_names(args: argparse.Namespace) -> list[str]:
    if getattr(args, "all", False):
        return list(EXTERNAL_SKILL_SOURCES.keys())

    raw = getattr(args, "skills", None)
    if not raw:
        raise SystemExit("--skills or --all is required")

    requested = [item.strip() for item in raw.split(",") if item.strip()]
    if "all" in requested:
        return list(EXTERNAL_SKILL_SOURCES.keys())

    unknown = [name for name in requested if name not in EXTERNAL_SKILL_SOURCES]
    if unknown:
        known = ", ".join(EXTERNAL_SKILL_SOURCES.keys())
        raise SystemExit(f"Unknown external skill(s): {', '.join(unknown)}. Known: {known}")

    unique: list[str] = []
    for name in requested:
        if name not in unique:
            unique.append(name)
    return unique


def resolve_install_skills_dir(args: argparse.Namespace) -> Path:
    if args.scope == "project":
        project_root = resolve_project_root(args)
        project_skills_dir = resolve_project_skills_dir(args, project_root)
        if not project_skills_dir:
            raise SystemExit("--project-root or --project-skills-dir is required for project skill installation")
        return project_skills_dir
    return expand_path(args.global_skills_dir) or default_global_skills_dir()


def external_install_plan(args: argparse.Namespace, selected: list[str], target_dir: Path) -> dict[str, object]:
    return {
        "mode": "install-external-skills",
        "scope": args.scope,
        "targetDir": str(target_dir),
        "forceOverwriteExisting": True,
        "replaceFlagProvided": bool(args.replace),
        "skills": [
            {
                "name": name,
                "repo": EXTERNAL_SKILL_SOURCES[name]["repo"],
                "target": str(target_dir / name),
                "targetExists": (target_dir / name).exists(),
            }
            for name in selected
        ],
    }


def print_external_install_plan(plan: dict[str, object], as_json: bool) -> None:
    if as_json:
        print(json.dumps(plan, indent=2, ensure_ascii=False))
        return

    print("External skill install plan")
    print(f"Scope: {plan['scope']}")
    print(f"Target skills dir: {plan['targetDir']}")
    print("Force overwrite existing: yes, existing targets are backed up first")
    for item in plan["skills"]:
        status = "exists" if item["targetExists"] else "missing"
        print(f"- {item['name']}: {item['target']} ({status})")
        print(f"  source: {item['repo']}")


def read_skill_frontmatter_name(skill_md: Path) -> str | None:
    try:
        lines = skill_md.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        lines = skill_md.read_text(errors="ignore").splitlines()
    except OSError:
        return None

    if not lines or lines[0].strip() != "---":
        return None
    for line in lines[1:80]:
        stripped = line.strip()
        if stripped == "---":
            return None
        if stripped.startswith("name:"):
            return stripped.split(":", 1)[1].strip().strip("'\"")
    return None


def discover_skill_dirs(repo_root: Path) -> list[Path]:
    dirs: list[Path] = []
    for skill_md in repo_root.rglob("SKILL.md"):
        try:
            rel = skill_md.relative_to(repo_root)
        except ValueError:
            continue
        if ".git" in rel.parts:
            continue
        dirs.append(skill_md.parent)
    return dirs


def source_dir_for_external_skill(repo_root: Path, skill_name: str) -> Path:
    spec = EXTERNAL_SKILL_SOURCES[skill_name]
    aliases = {str(alias) for alias in spec["aliases"]}
    candidates = discover_skill_dirs(repo_root)
    if not candidates:
        raise RuntimeError("no SKILL.md files found in cloned repository")

    by_dir_name = [candidate for candidate in candidates if candidate.name in aliases]
    if len(by_dir_name) == 1:
        return by_dir_name[0]

    by_frontmatter = [
        candidate
        for candidate in candidates
        if read_skill_frontmatter_name(candidate / "SKILL.md") in aliases
    ]
    if len(by_frontmatter) == 1:
        return by_frontmatter[0]

    repo = str(spec["repo"])
    if len(EXTERNAL_REPO_TO_SKILLS[repo]) == 1 and len(candidates) == 1:
        return candidates[0]

    rel_candidates = ", ".join(str(candidate.relative_to(repo_root)) for candidate in candidates[:20])
    if len(candidates) > 20:
        rel_candidates += ", ..."
    raise RuntimeError(f"could not uniquely locate {skill_name}; candidates: {rel_candidates}")


def clone_repo(repo: str, destination: Path) -> tuple[bool, str]:
    if not shutil.which("git"):
        return False, "git command not found"

    try:
        completed = subprocess.run(
            ("git", "clone", "--depth", "1", repo, str(destination)),
            check=False,
            capture_output=True,
            text=True,
            timeout=180,
        )
    except subprocess.TimeoutExpired:
        return False, "git clone timed out after 180 seconds"
    except OSError as exc:
        return False, str(exc)
    if completed.returncode == 0:
        return True, ""
    message = (completed.stderr or completed.stdout).strip()
    return False, message or f"git clone exited with {completed.returncode}"


def copy_external_skill(source: Path, target: Path) -> tuple[str, Path | None, str | None]:
    backup: Path | None = None
    if target.exists():
        backup = backup_path(target)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(target), str(backup))

    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(
        source,
        target,
        ignore=shutil.ignore_patterns(".git", "__pycache__", "*.pyc"),
    )

    failures = compare_tree(source, target, {".git", "__pycache__"})
    if failures:
        return "failed", backup, "verification failed: " + ", ".join(failures[:20])
    return ("replaced" if backup else "installed"), backup, None


def install_external_skills(args: argparse.Namespace) -> int:
    selected = parse_skill_names(args)
    target_dir = resolve_install_skills_dir(args)
    plan = external_install_plan(args, selected, target_dir)

    if not args.yes:
        print_external_install_plan(plan, args.json)
        print("Refusing to install external skills without --yes. Confirm with the user, then rerun with --yes.", file=sys.stderr)
        return 2
    if not args.json:
        print_external_install_plan(plan, False)

    repo_groups: dict[str, list[str]] = {}
    for name in selected:
        repo = str(EXTERNAL_SKILL_SOURCES[name]["repo"])
        repo_groups.setdefault(repo, []).append(name)

    results: list[dict[str, object]] = []
    with tempfile.TemporaryDirectory(prefix="kuno-onboard-external-skills-") as tmp:
        tmp_root = Path(tmp)
        for index, (repo, names) in enumerate(repo_groups.items(), start=1):
            repo_root = tmp_root / f"repo-{index}"
            ok, clone_error = clone_repo(repo, repo_root)
            if not ok:
                for name in names:
                    results.append(
                        {
                            "name": name,
                            "repo": repo,
                            "status": "failed",
                            "error": clone_error,
                        }
                    )
                continue

            for name in names:
                target = target_dir / name
                try:
                    source = source_dir_for_external_skill(repo_root, name)
                    status, backup, error = copy_external_skill(source, target)
                    results.append(
                        {
                            "name": name,
                            "repo": repo,
                            "source": str(source),
                            "target": str(target),
                            "status": status,
                            "backup": str(backup) if backup else None,
                            "error": error,
                        }
                    )
                except Exception as exc:  # noqa: BLE001 - report per-skill install failures without hiding others.
                    results.append(
                        {
                            "name": name,
                            "repo": repo,
                            "target": str(target),
                            "status": "failed",
                            "error": str(exc),
                        }
                    )

    payload = {
        "mode": "install-external-skills",
        "scope": args.scope,
        "targetDir": str(target_dir),
        "forceOverwriteExisting": True,
        "replaceFlagProvided": bool(args.replace),
        "plan": plan,
        "results": results,
    }
    post_check = build_check_results(args)
    payload["postCheck"] = post_check
    payload["installationReport"] = post_check["installationReport"]
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print("\nExternal skill install results")
        for item in results:
            print(f"- {item['name']}: {item['status']}")
            if item.get("target"):
                print(f"  target: {item['target']}")
            if item.get("backup"):
                print(f"  backup: {item['backup']}")
            if item.get("error"):
                print(f"  note: {item['error']}")
        print_installation_report(payload["installationReport"], "Final installation report")

    return 1 if any(item["status"] == "failed" for item in results) else 0


def default_shell_profile() -> Path:
    shell_name = Path(os.environ.get("SHELL", "")).name
    if shell_name == "zsh":
        return Path.home() / ".zshrc"
    if shell_name == "bash" and platform.system() == "Darwin":
        return Path.home() / ".bash_profile"
    if shell_name == "bash":
        return Path.home() / ".bashrc"
    return Path.home() / ".profile"


def ensure_profile_line(profile: Path, line: str, marker: str) -> bool:
    profile.parent.mkdir(parents=True, exist_ok=True)
    existing = profile.read_text(encoding="utf-8") if profile.exists() else ""
    if line in existing:
        return False
    prefix = "" if not existing or existing.endswith("\n") else "\n"
    with profile.open("a", encoding="utf-8") as handle:
        handle.write(f"{prefix}# {marker}\n{line}\n")
    return True


def ensure_npm(args: argparse.Namespace) -> int:
    before = check_npm_runtime()
    payload: dict[str, object] = {
        "mode": "ensure-npm",
        "platform": before["platform"],
        "before": before,
        "actions": [],
    }

    if before["npm"]["installed"]:
        payload["status"] = "already-installed"
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("npm is already available.")
            print(f"npm: {before['npm']['path']} ({before['npm']['version']})")
            print(f"node: {before['node']['path']} ({before['node']['version']})")
        return 0

    system = platform.system() or sys.platform
    if system == "Windows":
        payload["status"] = "unsupported-platform"
        payload["advice"] = (
            "Native Windows is not supported by the nvm-sh installer. Use WSL with nvm-sh, "
            "or install a Windows Node version manager such as nvm-windows/nvs, then rerun check."
        )
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("npm is missing, but native Windows cannot be fully configured by this nvm-sh installer.")
            print(payload["advice"])
        return 1

    install_actions = payload["actions"]
    install_actions.append(f"install or update nvm with {NVM_INSTALL_URL}")
    install_actions.append("install latest Node.js LTS with nvm")
    install_actions.append("set nvm default alias to lts/*")
    install_actions.append("switch current shell to Node.js LTS")

    if not args.yes:
        payload["status"] = "needs-confirmation"
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("npm is missing.")
            print(f"Platform: {system}")
            for action in install_actions:
                print(f"- {action}")
            print("Rerun with --yes after user confirmation.")
        return 2

    installer_tool = "curl" if shutil.which("curl") else "wget" if shutil.which("wget") else None
    if not installer_tool:
        payload["status"] = "failed"
        payload["error"] = "Neither curl nor wget is available to download the nvm installer."
        print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else payload["error"])
        return 1

    if installer_tool == "curl":
        install_script = f"curl -o- {NVM_INSTALL_URL} | bash"
    else:
        install_script = f"wget -qO- {NVM_INSTALL_URL} | bash"

    install_result = shell_result(install_script, timeout=300)
    if not install_result or install_result.returncode != 0:
        payload["status"] = "failed"
        payload["error"] = (install_result.stderr or install_result.stdout).strip() if install_result else "Unable to execute shell installer."
        print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else payload["error"])
        return 1

    node_script = (
        f"{nvm_load_script()}; "
        "nvm install --lts; "
        "nvm alias default 'lts/*'; "
        "nvm use --lts; "
        "node --version; "
        "npm --version"
    )
    node_result = shell_result(node_script, timeout=600)
    if not node_result or node_result.returncode != 0:
        payload["status"] = "failed"
        payload["error"] = (node_result.stderr or node_result.stdout).strip() if node_result else "Unable to run nvm after installation."
        print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else payload["error"])
        return 1

    after = check_npm_runtime()
    payload["after"] = after
    payload["status"] = "installed" if after["npm"]["installed"] else "failed"
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"ensure-npm status: {payload['status']}")
        if after["npm"]["installed"]:
            print(f"npm: {after['npm']['path']} ({after['npm']['version']})")
            print(f"node: {after['node']['path']} ({after['node']['version']})")
        else:
            print("npm still is not available in PATH. Restart the shell or source the profile file, then rerun check.")
    return 0 if after["npm"]["installed"] else 1


def install_rtk(args: argparse.Namespace) -> int:
    before = check_cli_tool(CLI_TOOLS[0])
    local_bin = Path.home() / ".local" / "bin"
    profile = expand_path(args.profile) or default_shell_profile()
    payload: dict[str, object] = {
        "mode": "install-rtk",
        "platform": platform.system() or sys.platform,
        "before": before,
        "installUrl": RTK_INSTALL_URL,
        "targetDir": str(local_bin),
        "profile": str(profile),
    }

    if before["installed"]:
        payload["status"] = "already-installed"
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("rtk is already installed and verified with `rtk gain`.")
            print(f"rtk: {before['path']} ({before['version']})")
        return 0

    if before.get("wrongPackageSuspected") and not args.replace_wrong:
        payload["status"] = "wrong-package-suspected"
        payload["advice"] = "An `rtk` command exists but `rtk gain` failed. Confirm whether to remove or replace it before installing rtk-ai/rtk."
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(payload["advice"])
            print("Rerun with --replace-wrong after user confirmation if replacement is intended.")
        return 2
    if before.get("verificationFailed") and not args.reinstall:
        payload["status"] = "verification-failed"
        payload["advice"] = (
            "`rtk --version` looks like rtk-ai/rtk, but `rtk gain` failed. "
            "Check RTK data directory permissions first, or rerun with --reinstall after user confirmation."
        )
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(payload["advice"])
        return 2

    system = platform.system() or sys.platform
    if system == "Windows":
        payload["status"] = "manual-required"
        payload["advice"] = (
            "Download the Windows release zip from rtk-ai/rtk, extract rtk.exe into a directory on PATH "
            "such as %USERPROFILE%\\.local\\bin, then verify with `rtk --version` and `rtk gain`."
        )
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print(payload["advice"])
        return 1

    if not args.yes:
        payload["status"] = "needs-confirmation"
        payload["actions"] = [
            f"run {RTK_INSTALL_URL}",
            f"ensure {local_bin} is in PATH via {profile}",
            "verify `rtk --version` and `rtk gain`",
        ]
        if args.json:
            print(json.dumps(payload, indent=2, ensure_ascii=False))
        else:
            print("rtk is missing or not verified.")
            for action in payload["actions"]:
                print(f"- {action}")
            print("Rerun with --yes after user confirmation.")
        return 2

    if before.get("wrongPackageSuspected") and args.replace_wrong and shutil.which("cargo"):
        run_command(("cargo", "uninstall", "rtk"), timeout=120)

    if not shutil.which("curl"):
        payload["status"] = "failed"
        payload["error"] = "curl is required for the rtk-ai/rtk quick install script."
        print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else payload["error"])
        return 1

    install_result = shell_result(f"curl -fsSL {RTK_INSTALL_URL} | sh", timeout=300)
    if not install_result or install_result.returncode != 0:
        payload["status"] = "failed"
        payload["error"] = (install_result.stderr or install_result.stdout).strip() if install_result else "Unable to run rtk installer."
        print(json.dumps(payload, indent=2, ensure_ascii=False) if args.json else payload["error"])
        return 1

    os.environ["PATH"] = f"{local_bin}{os.pathsep}{os.environ.get('PATH', '')}"
    profile_updated = ensure_profile_line(
        profile,
        'export PATH="$HOME/.local/bin:$PATH"',
        "Added by kuno-workflow-onboard-skills for rtk",
    )
    after = check_cli_tool(CLI_TOOLS[0])
    payload["after"] = after
    payload["profileUpdated"] = profile_updated
    payload["status"] = "installed" if after["installed"] else "failed"
    if args.json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    else:
        print(f"install-rtk status: {payload['status']}")
        if profile_updated:
            print(f"Updated PATH in {profile}")
        if after["installed"]:
            print(f"rtk: {after['path']} ({after['version']})")
            print("Verification passed: rtk gain")
        else:
            print("rtk was installed but did not pass `rtk gain`. Check PATH, release download, and name-collision risk.")
    return 0 if after["installed"] else 1


def build_operations(args: argparse.Namespace) -> list[Operation]:
    global_agents = expand_path(args.global_agents_path) or (default_codex_home() / "AGENTS.md")
    project_root = resolve_project_root(args)
    operations = [
        Operation(
            "codex global AGENTS.md",
            TEMPLATE_DIR / "agents" / "AGENTS.global.md",
            global_agents,
            "file",
        )
    ]

    if not args.skip_project_agents:
        project_root = resolve_project_root(args, required=True)
        operations.append(
            Operation(
                "project AGENTS.md",
                TEMPLATE_DIR / "agents" / "AGENTS.project.md",
                project_root / "AGENTS.md",
                "file",
            )
        )

    if project_root:
        operations.append(
            Operation(
                "project .gitignore",
                PROJECT_GITIGNORE_TEMPLATE,
                project_root / ".gitignore",
                "ensure-file-block",
            )
        )

    if args.skills_scope != "none":
        if args.skills_scope == "project":
            explicit = expand_path(args.project_skills_dir)
            if explicit:
                skills_root = explicit
            else:
                if not project_root:
                    raise SystemExit("--project-root or --project-skills-dir is required for project skills")
                skills_root = project_root / ".agent" / "skills"
        else:
            skills_root = expand_path(args.global_skills_dir) or default_global_skills_dir()

        for name, source in SKILL_SOURCES.items():
            target = skills_root / name
            operations.append(
                Operation(
                    f"skill {name}",
                    source,
                    target,
                    "dir",
                    source.resolve() == target.resolve(),
                )
            )

    return operations


def print_plan(mode: str, operations: list[Operation], as_json: bool) -> None:
    payload = {
        "mode": mode,
        "platform": platform.system() or sys.platform,
        "skillDir": str(SKILL_DIR),
        "operations": [
            {
                "label": op.label,
                "source": str(op.source),
                "target": str(op.target),
                "kind": op.kind,
                "targetExists": op.target.exists(),
                "sameLocation": op.same_location,
            }
            for op in operations
        ],
    }
    if as_json:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return

    print(f"Mode: {mode}")
    print(f"Platform: {payload['platform']}")
    for item in payload["operations"]:
        if item["sameLocation"]:
            exists = "same source and target"
        else:
            exists = "exists" if item["targetExists"] else "missing"
        print(f"- {item['label']}: {item['target']} ({exists})")


def operation_allows_existing_target(operation: Operation) -> bool:
    return operation.kind == "ensure-file-block"


def operation_result(
    operation: Operation,
    status: str,
    action: str,
    *,
    backup: Path | None = None,
    reason: str | None = None,
) -> dict[str, object]:
    result: dict[str, object] = {
        "label": operation.label,
        "target": str(operation.target),
        "kind": operation.kind,
        "status": status,
        "action": action,
    }
    if backup:
        result["backup"] = str(backup)
    if reason:
        result["reason"] = reason
    return result


def print_operation_report(results: list[dict[str, object]], heading: str = "Operation report") -> None:
    print(f"\n{heading}:")
    if not results:
        print("- none")
        return
    for item in results:
        print(f"- {item['label']}: {item['status']}")
        print(f"  target: {item['target']}")
        print(f"  action: {item['action']}")
        if item.get("backup"):
            print(f"  backup: {item['backup']}")
        if item.get("reason"):
            print(f"  reason: {item['reason']}")


def ensure_confirmed(args: argparse.Namespace, mode: str) -> None:
    if mode == "plan":
        return
    if not args.yes:
        raise SystemExit("Refusing to change files without --yes. Run plan first, then rerun with --yes.")


def run(mode: str, args: argparse.Namespace) -> int:
    if mode == "check":
        print_check_results(build_check_results(args), args.json)
        return 0
    if mode == "ensure-npm":
        return ensure_npm(args)
    if mode == "install-rtk":
        return install_rtk(args)
    if mode == "install-external-skills":
        return install_external_skills(args)

    if mode in {"init", "reset"} and not args.json:
        print_check_results(build_check_results(args), False)
        print("")

    operations = build_operations(args)
    print_plan(mode, operations, args.json)
    if mode == "plan":
        return 0

    ensure_confirmed(args, mode)

    active_operations = [op for op in operations if not op.same_location]
    conflicts = [
        op
        for op in active_operations
        if op.target.exists() and not operation_allows_existing_target(op)
    ]

    backups: list[tuple[Path, Path]] = []
    backup_by_target: dict[Path, Path] = {}
    for op in conflicts:
        backup = backup_path(op.target)
        op.target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(op.target), str(backup))
        backups.append((op.target, backup))
        backup_by_target[op.target] = backup

    operation_results: list[dict[str, object]] = []
    for op in active_operations:
        try:
            action = copy_operation(op)
            failures = verify_operation(op)
            if failures:
                operation_results.append(
                    operation_result(
                        op,
                        "failed",
                        action,
                        backup=backup_by_target.get(op.target),
                        reason="verification failed: " + ", ".join(failures[:20]),
                    )
                )
                continue

            status = "skipped" if action.startswith("skipped") else "success"
            operation_results.append(
                operation_result(
                    op,
                    status,
                    action,
                    backup=backup_by_target.get(op.target),
                )
            )
        except Exception as exc:  # noqa: BLE001 - report each file operation failure with context.
            operation_results.append(
                operation_result(
                    op,
                    "failed",
                    "error",
                    backup=backup_by_target.get(op.target),
                    reason=str(exc),
                )
            )

    failed_operations = [item for item in operation_results if item["status"] == "failed"]

    if backups:
        print("Backups:")
        for original, backup in backups:
            print(f"- {original} -> {backup}")

    if not args.json:
        print_operation_report(operation_results)

    if failed_operations:
        print("Verification failed:", file=sys.stderr)
        for item in failed_operations:
            print(f"- {item['label']}: {item.get('reason', 'unknown failure')}", file=sys.stderr)
        return 3

    print("Verification passed.")
    if not args.json:
        final_check = build_check_results(args)
        print_installation_report(final_check["installationReport"], "Final installation report")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Install or reset Kuno workflow AGENTS and skills.")
    subparsers = parser.add_subparsers(dest="mode", required=True)

    for mode in ("check", "plan", "init", "reset"):
        sub = subparsers.add_parser(mode)
        sub.add_argument("--project-root", help="Target project root for project AGENTS or project skills.")
        sub.add_argument("--skip-project-agents", action="store_true", help="Do not install project AGENTS.md.")
        sub.add_argument(
            "--skills-scope",
            choices=("global", "project", "none"),
            default="global",
            help="Install bundled skills globally, into the project, or not at all.",
        )
        sub.add_argument("--global-agents-path", help="Override Codex global AGENTS.md path.")
        sub.add_argument("--global-skills-dir", help="Override global skills directory.")
        sub.add_argument("--project-skills-dir", help="Override project-level skills directory.")
        sub.add_argument("--yes", action="store_true", help="Allow init/reset to write files.")
        sub.add_argument("--json", action="store_true", help="Print machine-readable plan.")

    install = subparsers.add_parser("install-external-skills")
    install.add_argument(
        "--skills",
        help="Comma-separated external skill names to install. Use 'all' for every known external skill.",
    )
    install.add_argument("--all", action="store_true", help="Install every known external referenced skill.")
    install.add_argument(
        "--scope",
        choices=("global", "project"),
        default="global",
        help="Install into the global skills directory or a project-level skills directory.",
    )
    install.add_argument("--project-root", help="Target project root for project-level skills.")
    install.add_argument("--global-skills-dir", help="Override global skills directory.")
    install.add_argument("--project-skills-dir", help="Override project-level skills directory.")
    install.add_argument(
        "--replace",
        action="store_true",
        help="Compatibility flag; external skill installs always back up and overwrite existing targets.",
    )
    install.add_argument("--yes", action="store_true", help="Allow external skill installation.")
    install.add_argument("--json", action="store_true", help="Print machine-readable plan and results.")

    npm = subparsers.add_parser("ensure-npm")
    npm.add_argument("--yes", action="store_true", help="Install nvm and Node.js LTS when npm is missing.")
    npm.add_argument("--json", action="store_true", help="Print machine-readable results.")

    rtk = subparsers.add_parser("install-rtk")
    rtk.add_argument("--yes", action="store_true", help="Install rtk-ai/rtk when missing.")
    rtk.add_argument(
        "--replace-wrong",
        action="store_true",
        help="If an existing rtk command fails `rtk gain`, allow replacing it after user confirmation.",
    )
    rtk.add_argument(
        "--reinstall",
        action="store_true",
        help="Reinstall when rtk exists but `rtk gain` verification fails.",
    )
    rtk.add_argument("--profile", help="Shell profile file to update with ~/.local/bin PATH.")
    rtk.add_argument("--json", action="store_true", help="Print machine-readable results.")

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return run(args.mode, args)


if __name__ == "__main__":
    raise SystemExit(main())
