# Kuno Workflow Onboard Reference

## Bundled Templates

This Skill installs only these bundled templates:

- `templates/agents/AGENTS.global.md` -> Codex global `AGENTS.md`
- `templates/agents/AGENTS.project.md` -> target project root `AGENTS.md`
- `templates/project/.gitignore` -> target project root `.gitignore`, when `--project-root` is provided
- `.` -> `kuno-workflow-onboard-skills` skill directory, when source and target differ
- `templates/skills/trellis-workflow/`
- `templates/skills/trellis-channel/`
- `templates/skills/project-validation/`
- `templates/skills/gherkin-bdd/`
- `templates/skills/maestro-mobile-e2e/`
- `templates/skills/lessons-record/`
- `templates/skills/book-refactoring-pass/`
- `templates/skills/book-legacy-change-safety/`
- `templates/skills/book-ddd-distilled-modeling/`
- `templates/skills/book-ddia-data-design/`
- `templates/skills/book-release-readiness/`

The repository root `AGENTS.md` is not an install template. It only governs this configuration excerpt repository.

There are no bundled MCP configuration templates. GitNexus MCP, Chrome DevTools MCP, Playwright MCP, and Maestro MCP are reported as manual setup checks only. The Maestro MCP manual check generates generic server config values and JSON / TOML examples with `JAVA_HOME` and `PATH`, but the user must still adapt them to the active Agent or IDE MCP config format.

## Conversation Flow

Use this sequence when the Skill is invoked:

1. Tell the user that the Skill will install or reset local Codex workflow configuration from bundled templates.
2. Ask whether they want `init` or `reset`.
3. Ask: "Is the current working directory `<cwd>` the target project root for project-level `AGENTS.md`?"
4. If the answer is no, ask for the project root path, or offer to skip project-level `AGENTS.md`.
5. If skipped, show the absolute path to `templates/agents/AGENTS.project.md` in this Skill directory and ask the user to confirm that they will handle it manually. If the user still provides a project root, continue to update project `.gitignore`.
6. Explain that skills install globally by default. Only use project-level skills if the user explicitly requests that and provides a project path or skills directory.
7. Run `check` and show the completed checklist.
8. If npm is missing, confirm the platform with the user, ask permission to install nvm + latest Node.js LTS, then run `ensure-npm`.
9. Rerun `check`; only then evaluate CLI tools such as `rtk`, `trellis`, and `gitnexus`.
10. For every missing CLI tool or Skill, ask whether to install it and confirm global vs project-level scope where applicable. Use explicit installer subcommands for approved items: `install-java`, `install-maestro`, `install-playwright-cli`, `install-rtk`, `install-caveman`, `ensure-npm`, or `install-external-skills`.
11. Install only user-approved missing items. Network or filesystem writes outside the workspace may require explicit approval.
12. Rerun `check`; present the final installation report with installed items, already-installed items skipped for install, failed or missing items, failure reasons, not-checked items, and manual configuration steps.
13. Run `plan` and show the target paths, including project `.gitignore` when a project root is provided.
14. Run `init` or `reset` only after the user has confirmed the plan.

## Preflight Check

Run this before every `init` and every `reset`:

```bash
python scripts/onboard.py check --project-root /path/to/project
```

If project-level `AGENTS.md` is skipped, still check global tools and global skills:

```bash
python scripts/onboard.py check --skip-project-agents
```

The check reports:

- Runtime availability for `npm`, `node`, and `nvm`.
- npm-backed CLI checks are skipped when npm is not usable. Run `ensure-npm` first, then rerun `check`.
- `rtk` CLI availability, version output, and `rtk gain` verification to avoid the unrelated same-name package.
- `trellis` CLI availability and version output when available.
- `gitnexus` CLI availability and version output when available.
- Java 17+ availability for Maestro. Use `java --version` first and fall back to `java -version`.
- Maestro CLI availability and version output when Java 17+ is available.
- Conditional Playwright CLI / `@playwright/test` project readiness when a project root is provided.
- Bundled Skill presence in global and, when a project root is provided, project-level skill directories, including Kuno workflow skills, `gherkin-bdd`, `maestro-mobile-e2e`, and bundled book-derived skills.
- Referenced Skill presence for mattpocock/skills 1.0+ canonical skills (`diagnosing-bugs`, `tdd`, `grill-me`, `grill-with-docs`, `grilling`, `domain-modeling`, `codebase-design`, `handoff`, `writing-great-skills`, `to-prd`, `to-issues`) plus `ui-ux-pro-max`, `impeccable`, `web-ui-autotest-generator`, and `seo-geo`.
- Interaction compression Skill presence for `caveman`, checked only in the user-level global skills directory.
- Manual setup checks for GitNexus MCP, Chrome DevTools MCP, Playwright MCP, Maestro MCP, and React Bits Pro project-specific prerequisites. The Maestro MCP check includes generic MCP server config values and examples that include env values for `JAVA_HOME` and `PATH`.
- A structured `installationReport` containing installed, runtime / CLI tools skipped because already installed, failed or missing, not-checked, and manual-configuration items.

`init` and `reset` also print this preflight checklist before copying files in normal text mode. For machine-readable automation, run `check --json` explicitly before `init --json` or `reset --json`.

After the check, present a concise checklist to the user:

```text
Runtime:
- npm: installed / missing

CLI tools:
- rtk: installed / missing / verification-failed / wrong-package-suspected
- trellis: installed / missing
- gitnexus: installed / missing
- java: installed / missing / incompatible
- maestro: installed / missing / not-checked
- Playwright CLI: available / missing / project-not-detected

Bundled skills:
- kuno-workflow-onboard-skills: installed / missing
- trellis-workflow: installed / missing
- gherkin-bdd: installed / missing

Referenced skills:
- diagnosing-bugs: installed / missing

Interaction compression skills:
- caveman: installed / missing

Manual checks:
- Chrome DevTools MCP: confirm MCP server visibility
- Playwright MCP: confirm MCP server visibility
- Maestro MCP: confirm MCP server visibility after Java 17+, Maestro CLI, `JAVA_HOME`, and MCP `PATH` are configured
```

Do not claim missing items were installed until a follow-up `check` confirms them or the relevant installer command reports success and the expected files / commands exist.

## Final Installation Report

Every `check` text output includes an installation report. `install-external-skills`, `init`, and `reset` also print a final installation report after their post-operation check in normal text mode. In JSON mode, `check --json` returns the same data under `installationReport`; `install-external-skills --json` also includes `postCheck` and `installationReport`.

The report is the user-facing completion summary and must include:

- Installed runtime items, CLI tools, and skills, including version, path, and scope when known.
- Already-installed runtime items and npm-installed CLI tools that should be skipped for installation unless the user requests reinstall, upgrade, replacement, or project-local installation.
- Installed skills as detected facts only. Selected bundled and external skills are not skipped because already installed; their existing targets are overwritten without backup.
- Failed or missing runtime items, CLI tools, and skills.
- A reason for every failed or missing item, such as command not found, verification failure, wrong-package suspicion, missing `SKILL.md`, or skipped CLI checks because npm is unavailable.
- A next step for every failed or missing item, including the suggested install command or repair path.
- Not-checked items, especially CLI tools skipped because npm is not usable yet.
- Manual configuration items, including GitNexus MCP setup, Chrome DevTools MCP setup, Playwright MCP setup, Maestro MCP setup with generated `command`, `args`, and env values, and React Bits Pro project skill prerequisites.

Manual configuration items are not treated as installed by the script. They remain `manual-required` until the user completes the steps and a later environment check confirms the tool is visible or usable.

## Operation Report

`init` and `reset` print an operation report after file writes and verification. This report is separate from the tool installation report and records each target file or directory operation.

When `--project-root` is provided, the operation report must include `project .gitignore` with:

- Target path: `<project-root>/.gitignore`.
- Action: `created`, `updated`, or `skipped-already-present`.
- Status: `success`, `skipped`, or `failed`.
- Failure reason when the write, append, or verification step fails.

Project `.gitignore` is updated with `templates/project/.gitignore` by ensuring the full template block exists in the target file. Existing project rules are preserved. If the template block already exists, the operation is skipped as already present. In `init`, an existing `.gitignore` does not count as an overwrite conflict because it is updated in place; in `reset`, it is also updated in place rather than backed up and replaced.

AGENTS targets use backup-and-overwrite semantics. When an existing Codex global `AGENTS.md` or project `AGENTS.md` is present, it is first renamed with the dated backup rule, then the template is copied into the target path.

Skill targets use overwrite-without-backup semantics. When an existing bundled skill directory or explicitly installed external skill directory is present, it is removed first, then the template or cloned skill is copied into the same target path. During `init` / `reset`, mattpocock external skills use detected-only migration: if the target skills root already contains old or current mattpocock skills, legacy directories are backed up to a timestamped backup directory, canonical 1.0+ skills and required dependency skills are installed or updated, and legacy directories such as `diagnose`, `write-a-skill`, and removed `zoom-out` are removed from that target root. If no mattpocock skills are detected, no external mattpocock skills are installed.

## Bundled Workflow Skills

The onboard bundle includes workflow skills that are installed from templates rather than external repositories:

| Skill | Primary use |
|---|---|
| `trellis-workflow` | Trellis lifecycle, task artifacts, workflow templates, before-dev, check, finish-work, update-spec, parent / child tasks, and BDD / TDD workflow overlays. |
| `trellis-channel` | Trellis Channel preflight, worker boundaries, review / validation coordination, and runtime safety rules. |
| `project-validation` | Validation command selection and reporting, including BDD traceability, Chrome DevTools MCP, Playwright, Maestro, and Web UI automation gates. |
| `gherkin-bdd` | Persistent BDD / Gherkin specs for user-visible behavior, `.feature` path rules, scenario quality, and scenario-to-test traceability. |
| `maestro-mobile-e2e` | Maestro Mobile / Hybrid flow generation from BDD scenarios, repo flow asset paths, report naming, and lazy-loaded real-device troubleshooting lessons. |
| `lessons-record` | Long-term lesson recording and Trellis lesson storage structure. |

## Bundled Book-Derived Skills

The onboard bundle includes five focused skills derived from `agent-rules-books` `mini`-style rules:

| Skill | Primary use |
|---|---|
| `book-refactoring-pass` | Behavior-preserving refactoring before or during implementation. |
| `book-legacy-change-safety` | Safe changes to weakly tested or unclear legacy code. |
| `book-ddd-distilled-modeling` | Lightweight domain language and bounded context modeling before PRD or design. |
| `book-ddia-data-design` | Data consistency, schema evolution, event, queue, cache, and cross-service data-flow checks. |
| `book-release-readiness` | Production-readiness review for services, jobs, queues, integrations, and deployment-sensitive changes. |

These skills are bundled, not installed from an external repository at onboarding time. They are optional on-demand lenses and do not replace project rules, Trellis artifacts, GitNexus, tests, `project-validation`, Playwright, Maestro, Chrome DevTools diagnostics, or human release review.

## Installation Decisions

When an item is missing, ask the user before installing:

- Install npm first through nvm + latest Node.js LTS?
- Install `rtk` globally from `rtk-ai/rtk`?
- Install `caveman` as a user-level global Codex / Agent Skill?
- Install `trellis` globally or project-level?
- Install `gitnexus` globally or project-level?
- Install Playwright CLI / `@playwright/test` into the target project after confirming the project needs Web E2E?
- Install Java 17+ for Maestro? Default is the latest OpenJDK Temurin 21 JDK from `https://github.com/adoptium/temurin21-binaries/releases`; user-selected Java versions must be 17 or higher.
- Install Maestro CLI into the local development environment or CI runner after Java 17+ is available?
- Install bundled Kuno workflow skills globally or project-level?
- Install referenced optional skills now, leave them for a later task, or skip them intentionally? If selected, existing skill targets are overwritten without backup.

Common CLI install commands are surfaced by `check` as suggestions:

```bash
python scripts/onboard.py ensure-npm --yes
python scripts/onboard.py install-rtk --yes
python scripts/onboard.py install-caveman --yes
python scripts/onboard.py install-java --major 21 --yes
python scripts/onboard.py install-maestro --yes
python scripts/onboard.py install-playwright-cli --project-root /path/to/project --yes
npm install -g @mindfoldhq/trellis
npm install -g gitnexus
npm install -D @mindfoldhq/trellis
npm install -D gitnexus
npm init playwright@latest
npm install -D @playwright/test
```

Use the user's package manager and project policy when they differ from these suggestions. If install fails, report:

- Item name.
- Scope requested by user.
- Command or action attempted.
- Error summary.
- Suggested next step, such as checking Node/npm availability, network access, package registry access, MCP configuration, license prerequisites, or manual installation docs.

## npm and nvm Bootstrap

CLI tool checks depend on npm being usable. If `check` reports npm missing, stop CLI tool checks and ask the user to confirm npm bootstrap.

For macOS and Linux:

```bash
python scripts/onboard.py ensure-npm --yes
```

The command installs or updates nvm with the official nvm install script, loads nvm, runs `nvm install --lts`, sets `nvm alias default 'lts/*'`, runs `nvm use --lts`, and verifies `node --version` and `npm --version`.

For native Windows, the nvm-sh installer is not supported. Guide the user to use WSL with nvm-sh, or a Windows Node version manager such as nvm-windows or nvs, then rerun:

```bash
python scripts/onboard.py check --project-root /path/to/project
```

If nvm installs successfully but npm is still unavailable, ask the user to restart the shell or source the profile file, then rerun `check`.

## RTK Installation

RTK must be the Rust Token Killer from `rtk-ai/rtk`. Always verify with:

```bash
rtk --version
rtk gain
```

If `rtk --version` succeeds but `rtk gain` fails, distinguish same-name package collision from an RTK verification failure such as data directory permissions. Do not overwrite or reinstall unless the user explicitly confirms.

Install on macOS or Linux after confirmation:

```bash
python scripts/onboard.py install-rtk --yes
```

The command runs the upstream quick installer, ensures `~/.local/bin` is on PATH via the active shell profile, then verifies `rtk gain`. If replacement of a wrong `rtk` is intended and Cargo is available:

```bash
python scripts/onboard.py install-rtk --replace-wrong --yes
```

If the binary appears to be `rtk-ai/rtk` but `rtk gain` fails, troubleshoot permissions first or reinstall after confirmation:

```bash
python scripts/onboard.py install-rtk --reinstall --yes
```

For native Windows, use the upstream Windows release zip: extract `rtk.exe` into a PATH directory such as `%USERPROFILE%\.local\bin`, then verify with `rtk --version` and `rtk gain`.

If RTK cannot be installed, it may be skipped, but report the exact failure and next checks: PATH, `~/.local/bin`, `curl`, release download access, Windows PATH setup, data directory permissions, or same-name package collision.

## Caveman Installation

`caveman` is an Agent reply compression Skill. It reduces token use in status updates, command-result summaries, code-reading notes, and other conversational output. It does not change code, tests, validation, Trellis stages, GitNexus analysis, or workflow decisions.

Check only the user-level global skills directory for:

```text
caveman/SKILL.md
```

When missing, explain its role and ask the user before installing:

```bash
python scripts/onboard.py install-caveman --yes
```

The command runs the official Codex skill installer:

```bash
npx --yes skills add JuliusBrussee/caveman -a codex
```

After installation, rerun:

```bash
python scripts/onboard.py check
```

Installing caveman only makes the Skill available. Do not automatically enable caveman mode after installation. Use it only when the user asks with `/caveman`, `use caveman`, `caveman mode`, `少说一点`, `减少 token`, `压缩输出`, or an equivalent request. Prefer clear prose for install confirmations, destructive actions, security warnings, PRD / design / implement review gates, long-lived project documents, and final validation reports.

## Playwright Project CLI

Playwright CLI is a project-level Web E2E dependency, not a global default.

When a project root is provided, check for:

- `package.json` containing `@playwright/test` or `playwright`
- `playwright.config.ts`, `playwright.config.js`, `playwright.config.mts`, or `playwright.config.cts`
- package scripts containing `playwright test`
- existing Web E2E directories such as `tests/e2e`, `e2e`, or project-specific equivalents

If Web E2E, Web regression, or `web-ui-autotest-generator` requires Playwright but the project does not have it, ask the user before installing. After confirmation, use the project package manager and project policy.

Common npm commands:

```bash
python scripts/onboard.py install-playwright-cli --project-root /path/to/project --yes
npm init playwright@latest
npm install -D @playwright/test
npx playwright install
```

The script command installs `@playwright/test` into the target project and runs `npx playwright install` by default. Use `--skip-browsers` only when the project or CI image already manages browser binaries.

If the user declines installation, report:

- `Playwright CLI`: `skipped-by-user`
- `Playwright Web Tests`: `blocked`

Chrome DevTools MCP or Playwright MCP may still be used for diagnostics and exploration, but do not claim Web E2E passed without running project Playwright tests.

## Maestro Java, CLI, and MCP

Maestro CLI requires Java 17 or newer. Check Java before checking or installing Maestro CLI:

```bash
java --version
java -version
```

Prefer the local machine's current JDK when it is 17 or newer. If the current `java` is missing or lower than 17, scan the local machine for another installed JDK that is 17 or newer and use that path for Maestro before proposing a new install. If no suitable installed JDK is found, ask the user before installing a JDK. The default recommendation is the latest OpenJDK Temurin 21 JDK from:

```text
https://github.com/adoptium/temurin21-binaries/releases
```

If the user requests another Java major version, only install versions 17 or higher. Refuse versions lower than 17. Install a JDK, not only a JRE, and verify:

- `java --version` or `java -version`
- `JAVA_HOME` points to the selected JDK
- `PATH` resolves the expected Java

After user confirmation, install the default Temurin 21 JDK with:

```bash
python scripts/onboard.py install-java --major 21 --yes
```

If the user explicitly requests another supported major version, pass that major version, for example:

```bash
python scripts/onboard.py install-java --major 17 --yes
```

Without `--yes`, `install-java` only prints `needs-confirmation` plus the planned actions. The onboard flow must not silently download or install Java.

After Java 17+ is available, check Maestro CLI:

```bash
maestro --help
maestro test --help
```

If Maestro CLI is missing, ask the user before installing it into the local development environment or CI runner. If installation is declined, report `Maestro CLI: skipped-by-user` and mark Maestro Mobile / Web Smoke as blocked or skipped as appropriate.

After user confirmation, install Maestro CLI with the official installer through the script:

```bash
python scripts/onboard.py install-maestro --yes
```

If a `maestro` command exists but fails verification, do not replace it silently. Troubleshoot Java and PATH first, then use `--reinstall --yes` only after explicit confirmation.

Maestro MCP depends on Maestro CLI and must be configured in the active Agent or IDE MCP client with the server command, args, and explicit environment variables. The required config values are:

```json
{
  "command": "maestro",
  "args": ["mcp"],
  "env": {
    "JAVA_HOME": "/path/to/jdk/Contents/Home",
    "PATH": "/Users/<user>/.maestro/bin:/path/to/jdk/Contents/Home/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
  }
}
```

For TOML-based MCP clients, the same values may be represented as:

```toml
[mcp_servers.maestro]
command = "maestro"
args = ["mcp"]

[mcp_servers.maestro.env]
JAVA_HOME = "/path/to/jdk/Contents/Home"
PATH = "/Users/<user>/.maestro/bin:/path/to/jdk/Contents/Home/bin:/usr/local/bin:/opt/homebrew/bin:/usr/bin:/bin:/usr/sbin:/sbin"
```

Build `JAVA_HOME` from the selected local JDK in this order: the current `java` executable's JDK home when it is 17+, existing `JAVA_HOME` when it is 17+, platform-discovered JDK homes such as macOS `/usr/libexec/java_home`, and known local JDK directories. If none satisfy Java 17+, ask before installing a new JDK. Build `PATH` with the Maestro bin directory first, the selected JDK `bin` directory second, and safe system directories after that. Do not configure Maestro MCP with only `command` and `args`; the MCP server process may not inherit the interactive shell environment.

Do not treat Maestro MCP as a separately installed package. If MCP is missing but CLI works, continue with `maestro test` for deterministic flow execution and report the MCP status separately.

## External Skill Repositories

Referenced external skills are not bundled under `templates/`. When the user confirms installation, pull them from these repositories:

| Skill | Repository |
|---|---|
| `diagnosing-bugs` | `https://github.com/mattpocock/skills.git` |
| `tdd` | `https://github.com/mattpocock/skills.git` |
| `grill-me` | `https://github.com/mattpocock/skills.git` |
| `grill-with-docs` | `https://github.com/mattpocock/skills.git` |
| `grilling` | `https://github.com/mattpocock/skills.git` |
| `domain-modeling` | `https://github.com/mattpocock/skills.git` |
| `codebase-design` | `https://github.com/mattpocock/skills.git` |
| `handoff` | `https://github.com/mattpocock/skills.git` |
| `writing-great-skills` | `https://github.com/mattpocock/skills.git` |
| `to-prd` | `https://github.com/mattpocock/skills.git` |
| `to-issues` | `https://github.com/mattpocock/skills.git` |
| `impeccable` | `https://github.com/pbakaus/impeccable.git` |
| `ui-ux-pro-max` | `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git` |
| `web-ui-autotest-generator` | `https://github.com/Cheryl-station/web-ui-autotest.git` |
| `seo-geo` | `https://github.com/ReScienceLab/opc-skills.git` |

Install approved missing external skills with:

```bash
python scripts/onboard.py install-external-skills \
  --skills diagnosing-bugs,tdd,grill-me \
  --scope global \
  --yes
```

Legacy input names are handled deliberately: `diagnose` is normalized to `diagnosing-bugs`, `write-a-skill` is normalized to `writing-great-skills`, and removed `zoom-out` is rejected with a migration note. Dependency skills are added automatically: `tdd` includes `codebase-design`, `grill-me` includes `grilling`, and `grill-with-docs` includes `grilling` and `domain-modeling`.

`seo-geo` is an optional public Web visibility Skill. Basic SEO/GEO audit does not require DataForSEO credentials; DataForSEO login/password only unlock enhanced keyword, SERP, backlink, and domain overview analysis. Treat those credentials and any paid search data as secrets and never write them to repositories, logs, screenshots, tests, or reports.

Install all known external referenced skills:

```bash
python scripts/onboard.py install-external-skills --all --scope global --yes
```

Install into a project-level skills directory:

```bash
python scripts/onboard.py install-external-skills \
  --skills ui-ux-pro-max,impeccable \
  --scope project \
  --project-root /path/to/project \
  --yes
```

External skills always overwrite existing target directories without backup after user confirmation. The `--replace` flag is accepted for older commands but is no longer required:

```bash
python scripts/onboard.py install-external-skills \
  --skills web-ui-autotest-generator \
  --scope global \
  --yes
```

The installer clones each repository into a temporary directory, discovers the matching `SKILL.md` directory by folder name or frontmatter `name`, removes an existing target directory when present, copies that whole skill directory, and verifies the copied files.

If external skill installation fails, usually continue with AGENTS / bundled skill setup and report the failed external item separately. Common causes are missing `git`, network restrictions, repository access failures, no matching `SKILL.md`, ambiguous `SKILL.md` candidates, or filesystem permissions.

## MCP Setup Boundary

MCP items are not installed by `install-external-skills`, `init`, or `reset`, and this bundle does not include MCP configuration templates. They are checked and reported, then configured with explicit user participation.

For GitNexus MCP:

1. Confirm the GitNexus CLI works, for example with `npx gitnexus status` in the target project.
2. Configure or enable the GitNexus MCP server in the active Agent or IDE MCP settings using the current GitNexus setup instructions. Choose the transport supported by that client, such as stdio, Streamable HTTP, or legacy SSE; do not copy a transport-specific config unless the user has selected it.
3. Restart or reload the Agent environment so the MCP server is discovered.
4. Confirm GitNexus MCP tools or resources are visible to the Agent, then check the target project index.
5. If the project is not indexed yet, run GitNexus analysis from the project root and re-check MCP visibility.

For Chrome DevTools MCP:

1. Configure or enable the Chrome DevTools MCP server in the active Agent or IDE MCP settings.
2. Confirm Google Chrome or Chrome for Testing is available when the MCP server requires it.
3. Restart or reload the Agent environment so the MCP server is discovered.
4. Confirm Chrome DevTools MCP tools are visible before relying on it for browser diagnostics.
5. Treat DevTools MCP output as diagnostic evidence, not as a replacement for project tests or Playwright E2E.

For Playwright MCP:

1. Configure or enable the Playwright MCP server in the active Agent or IDE MCP settings.
2. Restart or reload the Agent environment so the MCP server is discovered.
3. Confirm Playwright MCP tools are visible before relying on it for page exploration or locator assistance.
4. Do not treat Playwright MCP as a substitute for project-level Playwright CLI / `@playwright/test`.

For Maestro MCP:

1. Confirm Java 17+ and Maestro CLI work first.
2. Use the generated generic MCP server config from `check` or `install-maestro` as the starting point.
3. Adapt the values to the active Agent or IDE MCP config format, including `command = maestro`, `args = [mcp]`, `JAVA_HOME`, and a `PATH` that contains the Maestro bin directory and the JDK `bin` directory.
4. Restart or reload the Agent environment so the MCP server is discovered.
5. Confirm Maestro MCP tools are visible before relying on it for device inspection, view hierarchy, screenshots, or flow assistance.
6. If Maestro MCP is unavailable but Maestro CLI works, continue deterministic flow execution through `maestro test` and report MCP separately.

For React Bits Pro Skill:

1. Treat it as a conditional project skill, not a global default.
2. Confirm the target project is React with shadcn/ui initialized and `components.json` present.
3. Confirm `components.json` contains the required React Bits registry entries and the current environment can read `REACTBITS_LICENSE_KEY` without printing it.
4. If prerequisites are met but the project Skill is missing, run `npx shadcn@latest add @reactbits-starter/skill` from the project root.
5. Confirm the React Bits Pro `SKILL.md` exists in the project and rerun the onboard check.
6. Skip this item for non-React projects, projects without a license key, or projects that do not need React Bits Pro.

## Path Detection

The script uses `platform.system()` and `Path.home()` so the same commands work on macOS, Linux, and Windows.

Codex global AGENTS path:

1. `--global-agents-path`, if provided.
2. `$CODEX_HOME/AGENTS.md`, if `CODEX_HOME` is set.
3. `~/.codex/AGENTS.md`.

Global skills path:

1. `--global-skills-dir`, if provided.
2. `$AGENT_SKILLS_DIR`, if set.
3. `$CODEX_HOME/skills`, if `CODEX_HOME` is set.
4. `~/.codex/skills`.

Legacy paths such as `~/.agent/skills` are not used as automatic fallbacks. Use `--global-skills-dir ~/.agent/skills` or set `$AGENT_SKILLS_DIR` when a local machine intentionally uses that directory.

Project AGENTS path:

1. `--project-root/AGENTS.md`.
2. Project-level AGENTS is skipped when `--skip-project-agents` is passed.
3. `--project-root` must point to an existing directory; the script does not create a new project root.

Project `.gitignore` path:

1. `<project-root>/.gitignore` whenever `--project-root` is provided.
2. The template block is appended when the file exists and the block is not already present.
3. The file is created when it does not exist.

Project skills path:

1. `--project-skills-dir`, if provided.
2. `<project-root>/.agent/skills`.

## Init vs Reset

`init` and `reset` both back up and overwrite existing AGENTS files. Existing bundled skill directories are overwritten without backup. Project `.gitignore` is an update-in-place target, so an existing `.gitignore` does not get backed up or replaced.

Existing AGENTS targets are backed up before copying:

- Existing `AGENTS.md` files become `AGENTS.md.yyyy-mm-dd-index`.
- If the onboard Skill is already running from the same target directory it would install to, that self-install operation is treated as a no-op to avoid self-overwrite.
- Project `.gitignore` is updated in place by ensuring the template block exists; it is not backed up and replaced.
- Existing bundled skill directories are removed and copied again at the same path; no `<skill-name>.yyyy-mm-dd-index` backup is created.

The AGENTS backup index starts at `1` and increments within the same directory until a free backup path is found.

## Common Commands

Plan global onboarding and project AGENTS:

```bash
python scripts/onboard.py plan --project-root /path/to/project
```

Initialize global AGENTS, project AGENTS, and global skills:

```bash
python scripts/onboard.py init --project-root /path/to/project --yes
```

Reset the same targets:

```bash
python scripts/onboard.py reset --project-root /path/to/project --yes
```

Install only global AGENTS and global skills:

```bash
python scripts/onboard.py init --skip-project-agents --yes
```

Skip project AGENTS but still update project `.gitignore`:

```bash
python scripts/onboard.py init --project-root /path/to/project --skip-project-agents --yes
```

Install skills into a project:

```bash
python scripts/onboard.py init --project-root /path/to/project --skills-scope project --yes
```

Override all target paths:

```bash
python scripts/onboard.py reset \
  --global-agents-path /custom/codex/AGENTS.md \
  --global-skills-dir /custom/skills \
  --project-root /path/to/project \
  --yes
```

## Verification

After a successful `init` or `reset`, the script compares every copied file with its bundled template. Treat any verification failure as incomplete setup and do not claim onboarding succeeded.
