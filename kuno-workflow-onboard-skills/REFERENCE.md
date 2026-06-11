# Kuno Workflow Onboard Reference

## Bundled Templates

This Skill installs only these bundled templates:

- `templates/agents/AGENTS.global.md` -> Codex global `AGENTS.md`
- `templates/agents/AGENTS.project.md` -> target project root `AGENTS.md`
- `.` -> `kuno-workflow-onboard-skills` skill directory, when source and target differ
- `templates/skills/trellis-workflow/SKILL.md`
- `templates/skills/trellis-channel/SKILL.md`
- `templates/skills/project-validation/SKILL.md`
- `templates/skills/lessons-record/SKILL.md`

The repository root `AGENTS.md` is not an install template. It only governs this configuration excerpt repository.

## Conversation Flow

Use this sequence when the Skill is invoked:

1. Tell the user that the Skill will install or reset local Codex workflow configuration from bundled templates.
2. Ask whether they want `init` or `reset`.
3. Ask: "Is the current working directory `<cwd>` the target project root for project-level `AGENTS.md`?"
4. If the answer is no, ask for the project root path, or offer to skip project-level `AGENTS.md`.
5. If skipped, show the absolute path to `templates/agents/AGENTS.project.md` in this Skill directory and ask the user to confirm that they will handle it manually.
6. Explain that skills install globally by default. Only use project-level skills if the user explicitly requests that and provides a project path or skills directory.
7. Run `check` and show the completed checklist.
8. If npm is missing, confirm the platform with the user, ask permission to install nvm + latest Node.js LTS, then run `ensure-npm`.
9. Rerun `check`; only then evaluate CLI tools such as `rtk`, `trellis`, and `gitnexus`.
10. For every missing CLI tool or Skill, ask whether to install it and confirm global vs project-level scope where applicable.
11. Install only user-approved missing items. Network or filesystem writes outside the workspace may require explicit approval.
12. Rerun `check`; report installed, still missing, failed, and intentionally skipped items.
13. Run `plan` and show the target paths.
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
- CLI checks are skipped when npm is not usable. Run `ensure-npm` first, then rerun `check`.
- `rtk` CLI availability, version output, and `rtk gain` verification to avoid the unrelated same-name package.
- `trellis` CLI availability and version output when available.
- `gitnexus` CLI availability and version output when available.
- Bundled Skill presence in global and, when a project root is provided, project-level skill directories.
- Referenced Skill presence for `diagnose`, `tdd`, `grill-me`, `grill-with-docs`, `handoff`, `write-a-skill`, `zoom-out`, `to-prd`, `to-issues`, `ui-ux-pro-max`, `impeccable`, and `web-ui-autotest-generator`.
- Manual checks for GitNexus MCP, TestSprite MCP, and React Bits Pro project-specific prerequisites.

`init` and `reset` also print this preflight checklist before copying files in normal text mode. For machine-readable automation, run `check --json` explicitly before `init --json` or `reset --json`.

After the check, present a concise checklist to the user:

```text
Runtime:
- npm: installed / missing

CLI tools:
- rtk: installed / missing / verification-failed / wrong-package-suspected
- trellis: installed / missing
- gitnexus: installed / missing

Bundled skills:
- kuno-workflow-onboard-skills: installed / missing
- trellis-workflow: installed / missing

Referenced skills:
- diagnose: installed / missing

Manual checks:
- TestSprite MCP: confirm MCP server and API key
```

Do not claim missing items were installed until a follow-up `check` confirms them or the relevant installer command reports success and the expected files / commands exist.

## Installation Decisions

When an item is missing, ask the user before installing:

- Install npm first through nvm + latest Node.js LTS?
- Install `rtk` globally from `rtk-ai/rtk`?
- Install `trellis` globally or project-level?
- Install `gitnexus` globally or project-level?
- Install bundled Kuno workflow skills globally or project-level?
- Install referenced optional skills now, skip them, or leave them for a later task?

Common CLI install commands are surfaced by `check` as suggestions:

```bash
python scripts/onboard.py ensure-npm --yes
python scripts/onboard.py install-rtk --yes
npm install -g @mindfoldhq/trellis
npm install -g gitnexus
npm install -D @mindfoldhq/trellis
npm install -D gitnexus
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

## External Skill Repositories

Referenced external skills are not bundled under `templates/`. When the user confirms installation, pull them from these repositories:

| Skill | Repository |
|---|---|
| `diagnose` | `https://github.com/mattpocock/skills.git` |
| `tdd` | `https://github.com/mattpocock/skills.git` |
| `grill-me` | `https://github.com/mattpocock/skills.git` |
| `grill-with-docs` | `https://github.com/mattpocock/skills.git` |
| `handoff` | `https://github.com/mattpocock/skills.git` |
| `write-a-skill` | `https://github.com/mattpocock/skills.git` |
| `zoom-out` | `https://github.com/mattpocock/skills.git` |
| `to-prd` | `https://github.com/mattpocock/skills.git` |
| `to-issues` | `https://github.com/mattpocock/skills.git` |
| `impeccable` | `https://github.com/pbakaus/impeccable.git` |
| `ui-ux-pro-max` | `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git` |
| `web-ui-autotest-generator` | `https://github.com/Cheryl-station/web-ui-autotest.git` |

Install approved missing external skills with:

```bash
python scripts/onboard.py install-external-skills \
  --skills diagnose,tdd,grill-me \
  --scope global \
  --yes
```

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

For overwrite or reset-style installation, back up existing skill directories first:

```bash
python scripts/onboard.py install-external-skills \
  --skills web-ui-autotest-generator \
  --scope global \
  --replace \
  --yes
```

The installer clones each repository into a temporary directory, discovers the matching `SKILL.md` directory by folder name or frontmatter `name`, copies that whole skill directory, and verifies the copied files. Existing targets are skipped unless `--replace` is passed.

If external skill installation fails, usually continue with AGENTS / bundled skill setup and report the failed external item separately. Common causes are missing `git`, network restrictions, repository access failures, no matching `SKILL.md`, ambiguous `SKILL.md` candidates, or filesystem permissions.

## MCP Setup Boundary

MCP items are not installed by `install-external-skills`, `init`, or `reset`. They are checked and reported, then configured with explicit user participation.

For GitNexus MCP:

1. Confirm `gitnexus` CLI is installed.
2. Confirm the active Agent environment exposes GitNexus MCP tools.
3. Confirm the target project has a GitNexus index before using analysis results.
4. If any step is missing, guide the user through the current GitNexus install/config command for their environment, then re-check.

For TestSprite MCP:

1. Confirm the IDE or Agent MCP config contains the TestSprite server.
2. Confirm required API key or local auth is available without printing or storing secrets.
3. If the setup opens a local configuration portal, tell the user which fields they must complete.
4. Do not claim TestSprite testing is complete until the portal/configuration and environment access are confirmed.

For React Bits Pro Skill:

1. Treat it as a conditional project skill, not a global default.
2. Confirm the target project is React with shadcn/ui, `components.json`, registry configuration, and readable `REACTBITS_LICENSE_KEY`.
3. If prerequisites are missing, skip it and state what remains to configure.

## Path Detection

The script uses `platform.system()` and `Path.home()` so the same commands work on macOS, Linux, and Windows.

Codex global AGENTS path:

1. `--global-agents-path`, if provided.
2. `$CODEX_HOME/AGENTS.md`, if `CODEX_HOME` is set.
3. `~/.codex/AGENTS.md`.

Global skills path:

1. `--global-skills-dir`, if provided.
2. `$AGENT_SKILLS_DIR`, if set.
3. macOS / Linux fallback: `~/.codex/skills`.
4. Windows fallback: `%USERPROFILE%\.codex\skills`.

Legacy paths such as `~/.agent/skills` are not used as automatic fallbacks. Use `--global-skills-dir ~/.agent/skills` or set `$AGENT_SKILLS_DIR` when a local machine intentionally uses that directory.

Project AGENTS path:

1. `--project-root/AGENTS.md`.
2. Project-level AGENTS is skipped when `--skip-project-agents` is passed.
3. `--project-root` must point to an existing directory; the script does not create a new project root.

Project skills path:

1. `--project-skills-dir`, if provided.
2. `<project-root>/.agent/skills`.

## Init vs Reset

`init` is conservative. If any target already exists, it exits without changing files and tells the user to run `reset`.

`reset` backs up existing targets before copying:

- Existing `AGENTS.md` files become `AGENTS.md.yyyy-mm-dd-index`.
- Existing bundled skill directories become `<skill-name>.yyyy-mm-dd-index`.
- If the onboard Skill is already running from the same target directory it would install to, that self-install operation is treated as a no-op to avoid self-overwrite.

The index starts at `1` and increments within the same directory until a free backup path is found.

## Common Commands

Plan global onboarding and project AGENTS:

```bash
python scripts/onboard.py plan --project-root /path/to/project
```

Initialize global AGENTS, project AGENTS, and global skills:

```bash
python scripts/onboard.py init --project-root /path/to/project --yes
```

Reset the same targets with backups:

```bash
python scripts/onboard.py reset --project-root /path/to/project --yes
```

Install only global AGENTS and global skills:

```bash
python scripts/onboard.py init --skip-project-agents --yes
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
