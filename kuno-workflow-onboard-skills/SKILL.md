---
name: kuno-workflow-onboard-skills
description: Checks, installs, or resets Kuno Codex workflow tools, AGENTS templates, and bundled skills on a local machine. Use when onboarding, initializing, reinstalling, resetting, migrating, or validating Codex global AGENTS.md, project AGENTS.md, Trellis, GitNexus, or Kuno workflow skills.
---

# Kuno Workflow Onboard Skills

Use this Skill to onboard a local machine or project to the Kuno Codex workflow templates bundled in this Skill.

The bundled install templates are self-contained under `templates/`, including `templates/project/.gitignore` for project roots. The installer can also install this onboard Skill directory itself as a global or project skill when source and target differ. Do not read or install the source repository root `AGENTS.md`, `ENTRYPOINT.md`, `README.html`, `archive/`, or `docs/lessons.md` as target configuration templates.

## Required Questions

Before installing or resetting, ask and resolve these points:

1. Is the action `init` or `reset`?
2. Is the current working directory the target project root for project-level `AGENTS.md`?
3. If not, what is the target project root path, or should project-level `AGENTS.md` be skipped?
4. Should skills be installed globally, or as project-level skills? Default is global.
5. If project-level skills are requested, what is the target project root or explicit project skills directory?

If the user provides a project root, `init` or `reset` also ensures the bundled `templates/project/.gitignore` content exists in `<project-root>/.gitignore` and reports success, skip, or failure. If the user skips project-level `AGENTS.md`, provide the bundled template path `templates/agents/AGENTS.project.md` and ask them to confirm that this is the file they will use for manual setup.

## Workflow

1. Run the mandatory preflight check first:

```bash
python scripts/onboard.py check --project-root <project-root>
```

Summarize the runtime, CLI tool, bundled skill, referenced skill, and manual MCP / conditional project checks. The output must include the installation report with installed items, already-installed items skipped for install, failed or missing items, reasons, and manual configuration steps. If npm is missing, ask for confirmation and run `python scripts/onboard.py ensure-npm --yes` before any CLI tool check or install. Do not proceed to `init` or `reset` until the user confirms install or explicitly chooses to skip missing optional items.

2. Install any user-approved missing tools or skills, then rerun `check`. External referenced skills must be pulled from their configured GitHub repositories only after confirmation:

```bash
python scripts/onboard.py install-external-skills --skills diagnose,tdd --scope global --yes
```

For missing RTK, confirm with the user and run `python scripts/onboard.py install-rtk --yes`; for verification failure, use `--reinstall --yes` only after confirmation. Always verify with `rtk gain`. If installation fails, report the failed item, attempted action, likely cause, and recommended next step. MCP items are check-and-guide only; never claim MCP installation is complete unless the user has completed the listed manual steps and a later check confirms the tools are visible.

3. Run a dry-run plan:

```bash
python scripts/onboard.py plan --project-root <project-root>
```

4. For a new setup, run `init`. It refuses to overwrite existing targets:

```bash
python scripts/onboard.py init --project-root <project-root> --yes
```

5. For a reset, run `reset`. It backs up existing targets before copying:

```bash
python scripts/onboard.py reset --project-root <project-root> --yes
```

6. If project-level `AGENTS.md` is skipped and no project `.gitignore` update is needed:

```bash
python scripts/onboard.py init --skip-project-agents --yes
```

To skip project-level `AGENTS.md` but still update project `.gitignore`, include `--project-root <project-root>`.

7. If skills should be installed in the project instead of globally:

```bash
python scripts/onboard.py init --project-root <project-root> --skills-scope project --yes
```

Every `check`, external Skill install, `init`, or `reset` run must end with the installation report so the user sees all installed, skipped because already installed, failed or missing, not-checked, and manual-configuration items.

## Preflight Scope

The `check` command inspects:

- Runtime: `npm`, `node`, `nvm`; CLI checks run only after npm is usable.
- CLI tools: `rtk`, `trellis`, `gitnexus`.
- Bundled skills: `kuno-workflow-onboard-skills`, `trellis-workflow`, `trellis-channel`, `project-validation`, `lessons-record`.
- Referenced skills from the bundled templates, including mattpocock skills, `ui-ux-pro-max`, `impeccable`, and `web-ui-autotest-generator`.
- Manual checks that cannot be fully proven by filesystem inspection, including GitNexus MCP, TestSprite MCP, and React Bits Pro project skill prerequisites.

## Target Defaults

The script detects the current platform and uses these defaults:

- Codex global AGENTS: `$CODEX_HOME/AGENTS.md`, otherwise `~/.codex/AGENTS.md`.
- Global skills: `$AGENT_SKILLS_DIR`, otherwise platform default `~/.codex/skills` on macOS/Linux or `%USERPROFILE%\.codex\skills` on Windows. Use `--global-skills-dir` for legacy paths such as `~/.agent/skills`.
- Project AGENTS: `<project-root>/AGENTS.md`.
- Project `.gitignore`: `<project-root>/.gitignore`, when `--project-root` is provided.
- Project skills: `<project-root>/.agent/skills`.

All paths can be overridden with script flags. See [REFERENCE.md](REFERENCE.md) for exact commands, backup behavior, and troubleshooting.
