---
name: kuno-workflow-onboard-skills
description: Checks, installs, or resets Kuno Codex workflow tools, AGENTS templates, and bundled skills on a local machine. Use when onboarding, initializing, reinstalling, resetting, migrating, or validating Codex global AGENTS.md, project AGENTS.md, Trellis, GitNexus, or Kuno workflow skills.
---

# Kuno Workflow Onboard Skills

Use this Skill to onboard a local machine or project to the Kuno Codex workflow templates bundled in this Skill.

The bundled install templates are self-contained under `templates/`, including `templates/project/.gitignore` for project roots. `scripts/onboard.py` reports MCP items as manual setup checks and does not copy MCP configuration templates by itself. The repository root CLI installers, `install.sh` and `install.ps1`, can use those checks to configure selected MCP servers directly for a single target platform after explicit user confirmation. The installer can also install this onboard Skill directory itself as a global or project skill when source and target differ. Do not read or install the source repository root `AGENTS.md`, `ENTRYPOINT.md`, `README.html`, `archive/`, or `docs/lessons.md` as target configuration templates.

## Required Questions

Before installing or resetting, ask and resolve these points:

1. If using `install.sh` or `install.ps1`, which target platform should be configured: `codex`, `claude`, `kimi`, or `oh-my-pi` / `omp`? If `--platform` / `-Platform` is provided, do not ask again.
2. Is the action `init` or `reset`?
3. Is the current working directory the target project root for project-level `AGENTS.md`?
4. If not, what is the target project root path, or should project-level `AGENTS.md` be skipped?
5. Should skills be installed globally, or as project-level skills? Default is global.
6. If project-level skills are requested, what is the target project root or explicit project skills directory?
7. If `init` or `reset` targets a project root and that root has no `.trellis/`, what Trellis developer username should be used for `trellis init -u`?
8. Which Trellis platform flags, if any, should be passed to `trellis init`? Examples include `codex`, `claude`, `cursor`, `opencode`, `gemini`, and `pi`; multiple platforms are allowed.

If the user provides a project root, `init` or `reset` also ensures the bundled `templates/project/.gitignore` content exists in `<project-root>/.gitignore` and reports success, skip, or failure. If the user skips project-level `AGENTS.md`, provide the bundled template path `templates/agents/AGENTS.project.md` and ask them to confirm that this is the file they will use for manual setup.

## Root CLI Installers

The repository root provides two user-facing CLI installers:

```bash
./install.sh --platform codex
```

```powershell
.\install.ps1 -Platform codex
```

Both scripts are portable wrappers around this Skill directory and require `source-root` to point directly to `kuno-workflow-onboard-skills`, not to the repository root. If omitted, the default source root is `./kuno-workflow-onboard-skills` from the current working directory. If that directory is missing or incomplete, the script must print that the Kuno Onboard skill was not found and exit without installing anything.

Supported platform values are `codex`, `claude`, `kimi`, `oh-my-pi`, and `omp`; `omp` is an alias for `oh-my-pi`. The platform choice is single-select only.

The root installers keep these paths separate:

- `source-root`: the complete `kuno-workflow-onboard-skills` directory containing `SKILL.md`, `REFERENCE.md`, `scripts/onboard.py`, and `templates/`.
- `project-root`: the user's target project root.
- current working directory: only the default project-root candidate and the base for the default `./kuno-workflow-onboard-skills`.

The scripts first validate `source-root`, then run the same preflight, tool installation, bundled skill, external skill, plan, and `init` / `reset` flow described below. They also offer direct MCP configuration for the selected platform. `scripts/onboard.py` remains the source of truth for checks and template writes; the root scripts own the interactive platform UI, Trellis username / platform prompts, and MCP client-specific configuration commands.

## Workflow

1. Run the mandatory preflight check first:

```bash
python scripts/onboard.py check --project-root <project-root>
```

Summarize the runtime, CLI tool, bundled skill, referenced skill, manual MCP setup checks, and conditional project checks. The output must include the installation report with installed items, already-installed runtime / CLI tools skipped for install, failed or missing items, reasons, and manual configuration steps. If npm is missing, ask for confirmation and run `python scripts/onboard.py ensure-npm --yes` before any CLI tool check or install. Do not proceed to `init` or `reset` until the user confirms install or explicitly chooses to skip missing optional items.

When `init` or `reset` targets a project root, Trellis CLI must be installed and pass verification before the final project setup step. If `trellis` is missing or fails verification, ask the user whether to install or repair it before continuing. If the project root has no `.trellis/`, ask for the Trellis developer username and optional platform list before running the write step. Do not invent a username or platform default; if the user gives no platform, run `trellis init` without extra platform flags.

2. Install any user-approved missing tools or skills, then rerun `check`. External referenced skills must be pulled from their configured GitHub repositories only after confirmation. Skills are force-installed: existing bundled or external skill targets are overwritten without backup instead of skipped.

```bash
python scripts/onboard.py install-external-skills --skills diagnosing-bugs,tdd --scope global --yes
```

mattpocock/skills 1.0+ uses canonical names. The installer normalizes legacy `diagnose` to `diagnosing-bugs`, legacy `write-a-skill` to `writing-great-skills`, and rejects removed `zoom-out` with a migration note. Dependency skills are added automatically: `tdd` includes `codebase-design`, `grill-me` includes `grilling`, and `grill-with-docs` includes `grilling` and `domain-modeling`.

For missing RTK, confirm with the user and run `python scripts/onboard.py install-rtk --yes`; for verification failure, use `--reinstall --yes` only after confirmation. Always verify with `rtk gain`.

For missing caveman, explain that caveman compresses Agent replies for lower token use without changing code, tests, validation, or workflow decisions. Confirm with the user and run `python scripts/onboard.py install-caveman --yes`. The command chooses the official installer for the user's PC platform: macOS / Linux use `curl -fsSL https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.sh | bash`; native Windows uses `irm https://raw.githubusercontent.com/JuliusBrussee/caveman/main/install.ps1 | iex`. Installing caveman only makes the Skill available; do not enable caveman mode unless the user explicitly asks for it.

For missing or incompatible Java when Maestro is needed, tell the user Maestro requires Java 17+. Prefer the local machine's current JDK when it is 17+; if the current JDK is missing or lower than 17, use another installed JDK that is 17+ before suggesting a new install. Do not install Java automatically. Default new installs to the latest OpenJDK Temurin 21 JDK and run `python scripts/onboard.py install-java --major 21 --yes` only after user confirmation. If the user requests another Java major version, pass that version only when it is 17 or higher; refuse lower versions.

For missing Maestro CLI, confirm Java 17+ first, ask the user, then run `python scripts/onboard.py install-maestro --yes`. If a `maestro` command exists but fails verification, use `--reinstall --yes` only after the user confirms replacement or repair. After Maestro CLI is available, use the generated Maestro MCP server config from `check` or `install-maestro`; every Agent or IDE config format must include `command = maestro`, `args = [mcp]`, and env values for `JAVA_HOME` and `PATH` containing the Maestro bin directory and JDK `bin` directory.

For missing project-level Playwright CLI, install it only inside a target project that has `package.json` and needs Web E2E, Web regression, or `web-ui-autotest-generator` output. After confirmation, run `python scripts/onboard.py install-playwright-cli --project-root <project-root> --yes`. If the user declines, continue with Chrome DevTools MCP or Playwright MCP only as diagnostics / exploration fallback and report that project Web E2E was blocked or skipped.

Do not ask about React Bits during generic onboarding. If `check` reports `React Bits tier selection`, first explain that shadcn/ui covers normal application components and React Bits Free or paid tiers are optional sources for more expressive components, blocks, or landing sections. Ask whether the target project should stay with shadcn/ui only, add React Bits Free, or use an existing paid Starter / Pro / Ultimate entitlement. Paid tiers require explicit user confirmation and a readable `REACTBITS_LICENSE_KEY`; do not print, store, or commit the key. During `reset`, preserve any detected React Bits tier / registry and do not replace it with a default free tier without confirmation.

If installation fails, report the failed item, attempted action, likely cause, and recommended next step. When using `scripts/onboard.py` directly, MCP items are check-and-guide only. When using `install.sh` or `install.ps1`, MCP items can be configured directly after user confirmation; never claim MCP configuration is complete unless the platform command or config-file write succeeds and the final platform-specific list/check step is run or explicitly reported as unavailable.

3. Run a dry-run plan:

```bash
python scripts/onboard.py plan --project-root <project-root>
```

4. For a new setup, run `init`. Existing AGENTS targets are backed up and overwritten; existing bundled skill targets are overwritten without backup; project `.gitignore` is updated in place:

```bash
python scripts/onboard.py init --project-root <project-root> --trellis-user <username> --trellis-platform codex --yes
```

If the target project already has `.trellis/`, omit `--trellis-user` and `--trellis-platform`; the script reports Trellis init as skipped-existing. If the user selected multiple Trellis platforms, repeat `--trellis-platform` or pass a comma-separated list, for example `--trellis-platform codex --trellis-platform gemini` or `--trellis-platform codex,gemini`. The script runs `trellis init -u <username> ... --yes --skip-existing` only when `.trellis/` is absent, so existing project files are not overwritten by Trellis init.

5. For a reset, run `reset`. It uses the same behavior: AGENTS are backed up and overwritten, while bundled skills are overwritten without backup. If the target skills root already contains old or current mattpocock skills, reset also runs a detected-only external migration: legacy mattpocock skill directories are backed up, 1.0+ canonical skills and required dependency skills are installed or updated, and legacy directories such as `diagnose`, `write-a-skill`, and removed `zoom-out` are removed from that target root.

```bash
python scripts/onboard.py reset --project-root <project-root> --trellis-user <username> --trellis-platform codex --yes
```

After `init` or `reset` finishes template and Skill writes, always check the Trellis project setup report. If it reports `needs-user` or `blocked-missing-cli`, resolve that condition and rerun the same mode. If it reports `bootstrap-required`, treat the non-zero exit as a required Agent handoff rather than a file-copy failure, and do not finish onboarding yet: use the `trellis-workflow` Skill in the target project, read `.trellis/workflow.md` and the `.trellis/tasks/00-bootstrap-guidelines` task artifacts, run `$trellis-before-dev`, complete the bootstrap guideline work, run `$trellis-check`, and only then run `$trellis-finish-work`.

6. If project-level `AGENTS.md` is skipped and no project `.gitignore` update is needed:

```bash
python scripts/onboard.py init --skip-project-agents --yes
```

To skip project-level `AGENTS.md` but still update project `.gitignore`, include `--project-root <project-root>`.

7. If skills should be installed in the project instead of globally:

```bash
python scripts/onboard.py init --project-root <project-root> --skills-scope project --yes
```

Every `check`, external Skill install, `init`, or `reset` run must end with the installation report so the user sees all installed, runtime / CLI tools skipped because already installed, failed or missing, not-checked, and manual-configuration items. Skills are not skipped because already installed; selected skills are overwritten without backup.

## Preflight Scope

The `check` command inspects:

- Runtime: `npm`, `node`, `nvm`; npm-backed CLI checks run only after npm is usable.
- CLI tools: `rtk`, `trellis`, `gitnexus`.
- Conditional project tooling: Playwright CLI / `@playwright/test`, checked when a project root is provided and Web E2E assets or scripts are present or requested.
- Mobile E2E tooling: Java 17+ for Maestro, Maestro CLI, and Maestro MCP guidance, including generated generic MCP server config examples with `JAVA_HOME` and `PATH`.
- Bundled skills: `kuno-workflow-onboard-skills`, `trellis-workflow`, `trellis-channel`, `project-validation`, `gherkin-bdd`, `maestro-mobile-e2e`, `lessons-record`, `book-refactoring-pass`, `book-legacy-change-safety`, `book-ddd-distilled-modeling`, `book-ddia-data-design`, `book-release-readiness`, and `seo-geo`.
- Referenced skills from the bundled templates, including mattpocock skills, `ui-ux-pro-max`, `impeccable`, `web-ui-autotest-generator`, and `shadcn`.
- Interaction compression skills: `caveman`, checked only in the user-level global skills directory.
- Manual setup checks that cannot be fully proven or completed by filesystem inspection, including GitNexus MCP with generated `command` / `args` config when the local CLI path is detected, Chrome DevTools MCP, Playwright MCP, Maestro MCP with explicit `JAVA_HOME` / `PATH` config guidance, and React Bits tier-selection guidance only when a target React + shadcn/ui project is detected.

## Target Defaults

The script detects the current platform and uses these defaults:

- Codex global AGENTS: `$CODEX_HOME/AGENTS.md`, otherwise `~/.codex/AGENTS.md`.
- Global skills: `--global-skills-dir`, otherwise `$AGENT_SKILLS_DIR`, otherwise `$CODEX_HOME/skills`, otherwise `~/.codex/skills`. Use `--global-skills-dir` for explicit legacy paths such as `~/.agent/skills`; do not treat `~/.agent/skills` as the portable global default.
- Project AGENTS: `<project-root>/AGENTS.md`.
- Project `.gitignore`: `<project-root>/.gitignore`, when `--project-root` is provided.
- Project skills: `<project-root>/.agent/skills`.

All paths can be overridden with script flags. See [REFERENCE.md](REFERENCE.md) for exact commands, overwrite behavior, backup behavior for AGENTS, and troubleshooting.
