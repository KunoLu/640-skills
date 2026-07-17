# Kuno Workflow Onboard Reference

## Bundled Templates

- `templates/agents/AGENTS.global.md` → global Codex `AGENTS.md`
- `templates/agents/AGENTS.project.md` → each selected project root `AGENTS.md`
- `templates/project/.gitignore` → each selected project root `.gitignore`
- `templates/skills/**` → required global bundled Skills

AGENTS files are backed up before overwrite. Bundled Skill targets are overwritten without backup. Project `.gitignore` is updated in place by ensuring that the bundled block exists.

## Public Interfaces

### Bash

```bash
bash install.sh [options]
```

Important arguments:

- `--platform <codex|claude|kimi|oh-my-pi|omp>`
- `--projects-root <abs-path[,abs-path...]>`
- `--init-projects <abs-path[,abs-path...]>`
- `--action <init|reset>`
- `--source-root <path>`
- `--skip-project-agents`
- `--global-agents-path <path>`
- `--global-skills-dir <path>`
- `--trellis-user <name>`
- repeatable or comma-separated `--trellis-platform <name>`
- `--skip-trellis-init`
- `--skip-trellis-bootstrap`
- `--no-mcp`, `--dry-run`, `--yes`, `--no-color`

### PowerShell

```powershell
.\install.ps1 [options]
```

PowerShell uses the equivalent parameters `-Platform`, `-ProjectsRoot`, `-InitProjects`, `-Action`, `-SourceRoot`, `-SkipProjectAgents`, `-GlobalAgentsPath`, `-GlobalSkillsDir`, `-TrellisUser`, `-TrellisPlatform`, `-SkipTrellisInit`, `-SkipTrellisBootstrap`, `-NoMcp`, `-DryRun`, `-Yes`, and `-NoColor`.

`--project-root`, `-ProjectRoot`, `--skills-scope`, `-SkillsScope`, `--project-skills-dir`, and `-ProjectSkillsDir` are no longer public root-installer arguments.

## Project Root Contract

`--projects-root` / `-ProjectsRoot` accepts one or more existing absolute directories separated by English commas. `--init-projects` / `-InitProjects` accepts the same format and activates project-only mode.

Rules:

1. Relative paths are rejected.
2. Empty CSV elements are ignored.
3. Paths are resolved to canonical absolute paths.
4. Duplicates are processed once.
5. `projects-root` and `init-projects` are mutually exclusive.
6. `init-projects` cannot be combined with `action`.
7. A normal root-installer run that receives neither argument asks whether the current working directory is a project root, explains that multiple absolute paths can be supplied with English commas, and otherwise prompts for the CSV list.
8. A blank interactive project list means global-only onboarding.

When the Onboard Skill receives multiple repository paths without an explicit statement that they should be initialized, it must ask the user to confirm that those paths are the intended project initialization roots.

## Two Execution Modes

### Normal init/reset

Normal onboarding:

1. Resolves the target Agent platform.
2. Checks and, when required, installs the target Agent CLI globally.
3. Ensures npm is available because Trellis and GitNexus are mandatory global tools.
4. Runs the global preflight.
5. Installs missing global Trellis and GitNexus without a scope prompt.
6. Preserves the existing optional RTK, caveman, Java, and Maestro decisions.
7. Installs every missing required external Skill globally without a selection or scope prompt.
8. Optionally configures selected user/global MCP servers.
9. Checks project-only Playwright and React Bits conditions for every root.
10. Writes global AGENTS and all bundled Skills once.
11. Writes project AGENTS and `.gitignore` for every root.
12. Runs Trellis initialization and bootstrap detection for every root.

### Project-only init-projects

Project-only mode:

1. Resolves the Agent platform because project workflow and Trellis platform context may need it.
2. Skips target Agent CLI detection and installation.
3. Skips npm/Node/nvm, RTK, Trellis/GitNexus global preflight, Java, Maestro, caveman, bundled Skills, external Skills, global AGENTS, and MCP configuration.
4. Runs `check-projects` for the selected roots.
5. Offers only applicable project-local Playwright or React Bits decisions.
6. Writes project AGENTS and `.gitignore`.
7. Uses an already available global Trellis CLI when initialization is required; if it is unavailable, the affected projects are reported as blocked rather than installing the CLI.
8. Checks bootstrap guidelines for every root.

## Target Agent CLI Gate

| Platform | Command | Required global npm package |
|---|---|---|
| `codex` | `codex --version` | `@openai/codex@latest` |
| `claude` | `claude --version` | `@anthropic-ai/claude-code@latest` |
| `kimi` | `kimi --version` | `@moonshot-ai/kimi-code@latest` |
| `oh-my-pi` / `omp` | `omp --version` | `@oh-my-pi/pi-coding-agent@latest` |

Shared commands:

```bash
python scripts/onboard.py check-agent-cli --platform codex
python scripts/onboard.py install-agent-cli --platform codex --yes
```

Normal onboarding does not collect the action or project list until the required target CLI gate passes. Oh My Pi follows the requested npm path and is accepted only when `omp --version` succeeds.

## Required Global Tools

Trellis and GitNexus are global-only:

```bash
npm install -g @mindfoldhq/trellis@latest
npm install -g gitnexus@latest
```

The preflight no longer advertises `npm install -D @mindfoldhq/trellis` or `npm install -D gitnexus`. Project state remains local:

- Trellis: `<project-root>/.trellis/`
- GitNexus: `<project-root>/.gitnexus/`

RTK remains global but keeps its existing confirmation behavior. Verify the Rust Token Killer implementation with:

```bash
rtk --version
rtk gain
```

If `rtk gain` fails, distinguish a same-name package collision from a data-directory permission failure before replacing it.

## npm and nvm

Normal onboarding requires npm whenever mandatory global Trellis or GitNexus is missing. On macOS and Linux:

```bash
python scripts/onboard.py ensure-npm --yes
```

The command installs/loads nvm, installs the latest Node.js LTS, sets the default alias, switches to LTS, and verifies Node/npm.

Native Windows remains manual-required because the POSIX nvm-sh installer is not compatible. Use WSL, nvm-windows, nvs, or another approved Node.js installation, then rerun the installer.

Project-only mode never bootstraps npm. If a user chooses a project-local Playwright or React Bits action and npm/npx is unavailable, report that project action as blocked.

## Required Global Skills

The 14 bundled Skills are always global during normal init/reset:

1. `kuno-workflow-onboard-skills`
2. `trellis-workflow`
3. `trellis-channel`
4. `project-validation`
5. `gherkin-bdd`
6. `knowledge-base-integration`
7. `maestro-mobile-e2e`
8. `lessons-record`
9. `book-refactoring-pass`
10. `book-legacy-change-safety`
11. `book-ddd-distilled-modeling`
12. `book-ddia-data-design`
13. `book-release-readiness`
14. `seo-geo`

All 15 referenced external Skills are also required globally:

| Skill | Repository |
|---|---|
| `diagnosing-bugs`, `tdd`, `grill-me`, `grill-with-docs`, `grilling`, `domain-modeling`, `codebase-design`, `handoff`, `writing-great-skills`, `to-spec`, `to-tickets` | `https://github.com/mattpocock/skills.git` |
| `impeccable` | `https://github.com/pbakaus/impeccable.git` |
| `ui-ux-pro-max` | `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git` |
| `web-ui-autotest-generator` | `https://github.com/Cheryl-station/web-ui-autotest.git` |
| `shadcn` | `https://github.com/shadcn-ui/ui.git`, subpath `skills/shadcn` |

Install every missing external Skill:

```bash
python scripts/onboard.py install-external-skills --all --scope global --source auto --yes
```

`--scope project` is rejected. Direct normal `init` and `reset` ensure every external Skill exists globally before template writes; the root installers perform the same guarantee before invoking the final mode.

Source policies:

- `auto` (default): clone and validate the selected Skills from each upstream repository as one group; if upstream acquisition or source validation fails, lazily load and validate the matching vendored stable group. A valid upstream group does not require the stable manifest to be readable.
- `upstream`: require the current upstream repository to clone and validate; do not fall back.
- `stable`: skip Git and require the vendored stable manifest, checksum, frontmatter, and complete Skill tree to validate.

Preparation and commit are separate phases. Every selected Skill is resolved, copied into target-filesystem staging, and verified before any canonical or legacy target changes. Manifest paths, configured upstream subpaths, and license paths must remain relative to and contained by their declared roots; absolute paths, `..` traversal, and symlink escapes are rejected. Commit moves existing targets into a temporary rollback directory, installs every staged canonical target, and only then removes legacy aliases.

Fallback is limited to upstream source acquisition and validation failures: missing Git, clone failure or timeout, an unavailable revision/subpath, invalid Skill frontmatter/structure, or a source tree that contains symlinks. Stable manifest, containment, checksum, license, or snapshot validation failures are fatal whenever stable is required. Target-side staging, permission, disk, commit, and rollback failures never trigger stable fallback. A local commit failure attempts to restore all prior targets; if any restore step fails, the transaction reports and retains the rollback directory path instead of deleting the only remaining backup copy.

The vendored fallback lives at `assets/external-skills/stable/`. Its `MANIFEST.json` is the single source of truth for stable-set id, upstream repository, full commit SHA, upstream subpath, local stable path, tree SHA-256, and license/NOTICE files. The snapshots are upstream content copied unchanged. Do not hand-edit them.

Promote a reviewed repository revision explicitly:

```bash
python scripts/onboard.py promote-external-skills-stable \
  --repository <manifest-repository-id> \
  --revision <full-40-character-commit-sha> \
  --stable-set <yyyy-mm-dd.index> \
  --yes
```

Promotion updates every managed Skill from that repository as one group, refreshes its license files and digests, validates the entire candidate stable set, and then swaps the stable directory transactionally. It never runs during normal `init`, `reset`, or external installation.
If upstream changed canonical names, repository layout, or license paths, first review and update the manifest/configured source contract in the same repository change; promotion intentionally refuses to guess a new subpath.

Legacy aliases remain recognized for migration: `diagnose` → `diagnosing-bugs`, `write-a-skill` → `writing-great-skills`, `to-prd` → `to-spec`, and `to-issues` → `to-tickets`. Removed `zoom-out` is not installed. Automatic migration is legacy-only so already canonical external Skills are not cloned twice during every init/reset.

External Skill targets use a temporary rollback backup during an explicit install. The rollback copy is deleted after a successful commit or a complete restore; it is not a persistent user backup. An incomplete restore retains the directory and returns its path for manual recovery. Existing canonical Skills are treated as installed only when their complete source tree and `SKILL.md` frontmatter validate; an invalid canonical target is reinstalled before any valid legacy alias is removed. Legacy migration no longer clones upstream independently: canonical installation uses the shared source policy first, then the migration step backs up and removes remaining legacy directories.

## Skills That Keep Their Existing Scope

- `caveman`: user-level global only and still requires its existing explicit installation decision. Installation does not immediately enable a persistent reply mode, but runtime thresholds may automatically enter task-scoped `auto-lite` for repetitive intermediate updates. Generic exit commands disable automatic re-entry for the current task, session-level automatic opt-out takes precedence over task-level state, and explicit manual activation does not clear either automatic opt-out.
- React Bits Free/Starter/Pro/Ultimate: project-only and conditional.
- Project Playwright CLI / `@playwright/test`: project-only and conditional.

Java 17+ and Maestro CLI remain local development environment prerequisites, not project dependencies. They keep their existing conditional confirmation flow.

## Project Checks

Project-only status is available without global inspection:

```bash
python scripts/onboard.py check-projects \
  --projects-root /abs/project-one,/abs/project-two \
  --json
```

The result contains one entry per root:

- `projectRoot`
- `playwright`
- `reactBits`
- `trellis.initialized`
- `trellis.bootstrapRequired`
- canonical bootstrap task path when present

Normal `check` includes the same entries under `projectChecks` while global runtime/tools/Skills remain at the top level.

### Playwright

Playwright is applicable when the project already contains a Playwright dependency, config, script, or E2E directory. A generic `package.json` by itself is not enough to install Playwright automatically.

After confirmation:

```bash
python scripts/onboard.py install-playwright-cli \
  --project-root /one/project \
  --yes
```

This single-project argument belongs only to the project-local Playwright installer; the public root installer still uses plural `projects-root`.

### React Bits

React Bits tier selection is shown only when the root is a React project and contains `components.json`.

- Default: keep shadcn/ui only.
- Free: require an explicitly configured free registry item before running `npx shadcn@latest add <registry-item>` in that project.
- Paid: require an existing entitlement and readable `REACTBITS_LICENSE_KEY`; never print or persist it. When prerequisites pass, add `@reactbits-starter/skill` from the project root.
- Reset: preserve the detected tier and registry.

## Multi-Project Trellis Setup

All selected roots share the provided Trellis username and platform flags, but each root is evaluated independently.

For every root:

1. If `.trellis/` exists, report `skipped-existing`.
2. If it is missing and no username was provided, report `needs-user` for that root.
3. Otherwise run:

```bash
trellis init -u <username> [--platform-flags] --yes --skip-existing
```

4. Confirm `.trellis/` was created.
5. Unless skipped, check only `.trellis/tasks/00-bootstrap-guidelines`.
6. If present, report `bootstrap-required` with the root and task path.

Processing continues for all roots even when an earlier root has a bootstrap task. Aggregate status priority is:

```text
failed > blocked > needs-user > bootstrap-required > success > skipped
```

A bootstrap task requires the Agent to enter that project, use `trellis-workflow`, read `.trellis/workflow.md` and the task artifacts, run `$trellis-before-dev`, complete the guideline work, run `$trellis-check`, and finish with `$trellis-finish-work`.

## MCP Setup

MCP configuration remains optional and interactive in normal mode. Project-only mode skips it.

Built-in choices:

- Chrome DevTools MCP: `npx -y chrome-devtools-mcp@latest`
- Playwright MCP: `npx -y @playwright/mcp@latest`
- Maestro MCP: `maestro mcp` with `JAVA_HOME` and `PATH`
- GitNexus MCP: detected global `gitnexus` executable with `args = [mcp]`
- Custom stdio MCP: user-provided command/args/env

Fixed platform scopes:

- Codex: user-level `codex mcp add` behavior.
- Claude Code: `claude mcp add --transport stdio --scope user ...`.
- Kimi Code: `kimi mcp add --transport stdio ...` with its default scope behavior.
- Oh My Pi: merge into `~/.omp/agent/mcp.json` only.

Do not write project-level Claude MCP entries or `<project-root>/.omp/mcp.json`. Do not expose secrets in logs or reports.

Maestro MCP is not a separate package. Java 17+ and Maestro CLI must pass first. Native Windows Java/Maestro automatic installation remains unavailable.

## Paths

Global AGENTS:

1. `--global-agents-path`
2. `$CODEX_HOME/AGENTS.md`
3. `~/.codex/AGENTS.md`

Global Skills:

1. `--global-skills-dir`
2. `$AGENT_SKILLS_DIR`
3. `$CODEX_HOME/skills`
4. `~/.codex/skills`

Project paths, repeated for every selected root:

- `<project-root>/AGENTS.md`
- `<project-root>/.gitignore`
- `<project-root>/.trellis/`
- `<project-root>/.trellis/tasks/00-bootstrap-guidelines`
- conditional project Playwright dependencies/configuration
- conditional React Bits Skill/registry

Generic bundled/external workflow Skills are never installed under `<project-root>/.agent/skills` by this onboard flow.

## Shared Python Commands

```bash
python scripts/onboard.py check --projects-root /abs/one,/abs/two
python scripts/onboard.py check-projects --projects-root /abs/one,/abs/two
python scripts/onboard.py plan --projects-root /abs/one,/abs/two
python scripts/onboard.py init --projects-root /abs/one,/abs/two --trellis-user your-name --yes
python scripts/onboard.py reset --projects-root /abs/one,/abs/two --trellis-user your-name --yes
python scripts/onboard.py init-projects --projects-root /abs/one,/abs/two --trellis-user your-name --yes
```

Global-only onboarding is still supported by omitting `--projects-root` and explicitly skipping project AGENTS when using the Python command directly:

```bash
python scripts/onboard.py init --skip-project-agents --yes
```

## Verification

After writes:

1. Verify every copied AGENTS file against its source template.
2. Verify every bundled global Skill directory recursively.
3. Verify the project `.gitignore` block exists in every selected root.
4. Report per-root Trellis init and bootstrap status.
5. Report per-root Playwright and React Bits decisions without claiming optional installation succeeded unless the command and post-check pass.
6. Rerun the target Agent CLI and global preflight after normal onboarding.
7. Rerun only `check-projects` after project-only onboarding.

Network failures, permissions, missing npm/npx, unsupported native Windows bootstrap, failed Trellis initialization, missing React Bits registry/license prerequisites, and bootstrap-required handoffs must remain explicit in the final report.
