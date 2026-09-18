# SBTD Workflow Onboard Reference

## Bundled Templates

- `templates/agents/AGENTS.global.md` -> global Codex `AGENTS.md`, and `~/.omp/agent/AGENTS.md` when `~/.omp` already exists
- `templates/agents/AGENTS.project.md` → each selected project root `AGENTS.md`
- `templates/project/.gitignore` → each selected project root `.gitignore`
- `templates/skills/**` → required global bundled Skills

`catalog.json` is the runtime source of truth for these paths, all bundled Skill ids, and every external Skill repository/subpath/alias. `catalog.schema.json` defines its Draft 2020-12 contract; `examples/catalog.minimal.json` is the minimal valid shape. The root installers require both catalog files, and `scripts/onboard.py` rejects duplicate ids, absolute or escaping paths, malformed HTTPS repository URLs, invalid kind/id/target-role combinations, wrong local source types, missing sources, and bundled Skill frontmatter identity mismatches before processing a command.

> **Staged v2 delivery (unreleased):** canonical payload is 14 bundled / 19 external Skills. Project setup now uses read-only SBTD checks without Trellis installation or initialization. Graft/host integration, task operations, identity creation and legacy migration remain staged work; this is not a completed v2 release. Existing legacy data is preserved; user-global retirement remains P1-13.

The P1-01 argument/codec modules and `onboard-contracts.schema.json` are internal executable contracts, not a second CLI or an activation of migration/recovery handlers. The existing command reference below remains the active public surface until each runtime/caller cutover. Contract validation checks declared structures and relationships; filesystem safety, authorization and actual operations remain stage-owned.

For validation, install the declared dependency with the interpreter that will load the installed Skill: `python -m pip install -r /path/to/installed/sbtd-workflow-onboard/requirements.txt`. A Skill directory copy does not perform this step. Imports remain lazy, missing dependencies fail closed, and availability must be checked from the installed copy rather than inferred from source-tree CI.

AGENTS files are backed up before overwrite. On `reset`, bundled Skill targets are overwritten without backup after their catalog sources pass the startup checks above. On `init`, a bundled Skill target that is already a valid Skill shell is skipped; missing or invalid shells are copied. After the canonical `sbtd-workflow-onboard` target validates, the legacy `kuno-workflow-onboard-skills` directory is removed without leaving an alias only when its own `SKILL.md` frontmatter confirms the legacy identity. An unrelated or mismatched legacy path blocks `init` / `reset` before target changes and remains untouched; deletion errors are returned as migration failures. Project `.gitignore` is updated in place by ensuring that the bundled block exists.


## Official Skills CLI Bootstrap

Install only the self-contained Onboard Skill from the public repository:

```bash
npx --yes skills@latest add \
  https://github.com/KunoLu/640-skills \
  --skill sbtd-workflow-onboard \
  --global \
  --agent codex \
  --yes \
  --copy
```

Use an authenticated `git+ssh://` source for a private repository. The source must expose `sbtd-workflow-onboard/SKILL.md`; the official CLI recursively discovers that Skill and copies the complete directory, including `REFERENCE.md`, `catalog.json`, `catalog.schema.json`, `scripts/`, `templates/`, and `assets/`.

The official CLI is a package bootstrap only. It does not run Onboard, install the catalog's bundled/external Skills, write AGENTS files, install Trellis/GitNexus, or initialize projects. After bootstrap, invoke the installed Skill and use its `scripts/onboard.py` interface. The repository root `install.sh` and `install.ps1` remain the complete interactive installation interfaces for a cloned checkout.

Installed `scripts/onboard.py` resolves its global Skills root in this order: explicit `--global-skills-dir`, `$AGENT_SKILLS_DIR`, the installed `sbtd-workflow-onboard` directory's parent when it is under a recognized global Agent Skills root, then the existing platform default. JSON `plan` and `check` output includes `globalSkillsDirSource` so this decision is auditable.

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
- `--no-mcp`, `--dry-run`, `--yes`, `--no-color`

The Agent platform selects the CLI and MCP adapter; it does not select the global AGENTS target. Normal onboarding keeps the Codex global AGENTS default shown under [Paths](#paths) unless `--global-agents-path` / `-GlobalAgentsPath` explicitly overrides it. If the user-home `.omp` directory already exists (POSIX `~/.omp`, Windows `%USERPROFILE%\.omp`), `init` / `reset` also backup-then-overwrite the same template to `~/.omp/agent/AGENTS.md`. Missing `.omp` is skipped; Onboard does not create `.omp`. `--global-agents-path` overrides only the Codex target. Project-only mode never writes global AGENTS.

### PowerShell

```powershell
.\install.ps1 [options]
```

PowerShell uses `-Platform`, `-ProjectsRoot`, `-InitProjects`, `-Action`, `-SourceRoot`, `-SkipProjectAgents`, `-GlobalAgentsPath`, `-GlobalSkillsDir`, `-NoMcp`, `-DryRun`, `-Yes`, and `-NoColor`. Trellis username/platform/skip options are removed in both installers and Python, without aliases.

`--yes` / `-Yes` answers yes/no prompts and skips final execution confirmation. It does not invent platform, action or React Bits text/selection answers, authorize migration, or override project-state conflicts.

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
2. May inspect the target Agent CLI read-only before collecting the remaining inputs.
3. Resolves all project roots and AGENTS scope, then runs complete `check-projects` before any installation or configuration write.
4. Repairs the selected Agent/npm only after project preflight passes, then runs the global preflight.
5. Installs missing global GitNexus without a scope prompt; no Trellis installation.
6. Preserves the existing optional RTK, caveman, Java, and Maestro decisions.
7. For `init`, installs only missing or invalid required external Skills globally. For `reset`, force-reinstalls every required external Skill from the current stable snapshot.
8. Optionally configures selected user/global MCP servers.
9. Checks project-only Playwright and React Bits conditions for every root.
10. Writes global AGENTS with backup-then-overwrite. For `init`, copies missing or invalid bundled Skills and skips valid Skill shells. For `reset`, overwrites every bundled Skill without backup.
11. Inspects every selected project's minimal SBTD state and scaffold destinations before Python installation writes; conflicts stop the batch.
12. Writes project AGENTS and `.gitignore`, preserving optional task/identity/spec/lessons data, then reports SBTD checks again.


### Project-only init-projects

Project-only mode:


1. Resolves the selected Agent platform for the existing adapter context.
2. Skips target Agent CLI detection and installation.
3. Skips npm/Node/nvm, RTK, Trellis/GitNexus global preflight, Java, Maestro, caveman, bundled Skills, external Skills, global AGENTS, and MCP configuration.
4. Runs complete read-only `check-projects` with the actual `--skip-project-agents` scope before any optional project install.
5. Offers only applicable project-local Playwright or React Bits decisions.
6. Writes project AGENTS and `.gitignore`.
7. Requires no Trellis CLI, developer name or pre-existing task state.
8. Reports an explicitly present unfinished SBTD bootstrap task without creating one.

The project AGENTS provides the existing minimum routing/safety fallback; project-only mode does not install or claim activation of global Skills. Missing optional tools do not freeze unrelated safe default/lite work, and no missing reviewer may be reported as passed.

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

The transitional GitNexus CLI remains global-only until its Graft cutover:

```bash
npm install -g gitnexus@latest
```

Project-local CLI installation is not offered. Trellis is no longer installed or invoked; existing legacy state is retained for explicit migration.
- GitNexus: `<project-root>/.gitnexus/`

RTK remains global but keeps its existing confirmation behavior. Verify the Rust Token Killer implementation with:

```bash
rtk --version
rtk gain
```

If `rtk gain` fails, distinguish a same-name package collision from a data-directory permission failure before replacing it.

## npm and nvm

Normal onboarding requires npm for the selected Agent and remaining GitNexus installation. On macOS and Linux:

```bash
python scripts/onboard.py ensure-npm --yes
```

The command installs/loads nvm, installs the latest Node.js LTS, sets the default alias, switches to LTS, and verifies Node/npm.

Native Windows remains manual-required because the POSIX nvm-sh installer is not compatible. Use WSL, nvm-windows, nvs, or another approved Node.js installation, then rerun the installer.

Project-only mode never bootstraps npm. If a user chooses a project-local Playwright or React Bits action and npm/npx is unavailable, report that project action as blocked.

## Required Global Skills

The 14 bundled Skills are always global during normal init/reset:

1. `sbtd-workflow-onboard`
2. `sbtd-task`
3. `project-validation`
4. `web-ui-autotest-generator`
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

The retired `trellis-workflow` and `trellis-channel` bundled Skills were removed from the catalog and the template tree in the same atomic change that added `sbtd-task` (source `templates/skills/sbtd-task`); no alias or compatibility copy is installed. User-global copies of the retired directories are deliberately left untouched by this change — their retirement cleanup is owned by P1-13.

The Onboard rename is a bundled migration: normal `plan` reports any detected legacy target, and normal `init` / `reset` removes it only after the canonical `sbtd-workflow-onboard/SKILL.md` exists with matching frontmatter. Project-only `init-projects` never inspects or modifies global Skill directories.

All 19 referenced external Skills are also required globally:

| Skill | Repository |
|---|---|
| `diagnosing-bugs`, `tdd`, `grill-me`, `grill-with-docs`, `grilling`, `domain-modeling`, `codebase-design`, `handoff`, `writing-for-agents`, `to-spec`, `to-tickets` | `https://github.com/mattpocock/skills.git` |
| `impeccable` | `https://github.com/pbakaus/impeccable.git` |
| `ui-ux-pro-max` | `https://github.com/nextlevelbuilder/ui-ux-pro-max-skill.git` |
| `shadcn` | `https://github.com/shadcn-ui/ui.git`, subpath `skills/shadcn` |
| `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt` | `https://github.com/DietrichGebert/ponytail.git`, subpaths `skills/<name>` |
| `i-have-adhd` | `https://github.com/ayghri/i-have-adhd.git`, subpath `skills/i-have-adhd` |

### Ponytail Provider Boundary

The four Ponytail Skills are ordinary required external Skills: no install confirmation, no optional group, and a missing or invalid copy is installed or repaired from the vendored stable set with the same transaction semantics as every other required Skill. Onboard is the stable skill-only provider and never installs, enables, disables, trusts, or removes the official Ponytail plugin; `ponytail-gain` and `ponytail-help` belong only to that plugin and are never Onboard-managed.

`check --json` reports `ponytailProvider` with `provider` (`onboard-stable` / `conflict` / `unknown`), `skillStatus` (`complete` / `partial` / `missing` / `invalid`), `pluginStatus` (`installed-enabled` / `installed-disabled` / `missing` / `cli-unavailable`), per-platform detail, and `nextStep`. Detection is read-only: Codex uses `codex plugin list --json`; OMP uses `omp plugin list --json` only when `~/.omp` already exists, because merely starting an unconfigured OMP CLI may create that directory. A missing `~/.omp` reports OMP as `not-configured` without invoking the CLI. Codex matches only canonical `ponytail@ponytail` (or name `ponytail` with marketplace `ponytail`); OMP matches name `ponytail` only when its source / install spec normalizes to the official `github.com/DietrichGebert/ponytail` repository. Same-named third-party packages never count.

An enabled official plugin is `provider=conflict`: `check` exits non-zero and `init` / `reset` block before writing stable copies; the root installers stop with the same guidance. The remedy is manual — disable or remove the plugin with the platform's own CLI, then rerun. An installed-but-disabled plugin is reported without blocking. When any platform CLI cannot be queried or its output cannot be parsed (and no enabled plugin was proven on the other platform), `provider=unknown`: Onboard neither fabricates a clean state nor blocks on unproven conflict.

The runtime gate contracts become active only after normal `init` / `reset` successfully writes the global rules and installs the required bundled / external Skills. The public Skills CLI bootstrap and `init-projects` do not activate these runtime gates by themselves. Installed global `AGENTS.md`, project rules, bundled `sbtd-task`, and bundled reviewer Skills jointly own the execution contract.

The `Book Gate Plan` uses objective predicates and explicit lifecycle states and is produced up front by `strict` tasks. `default` / `lite` tasks select methods by actual risk and explicit deliverables and never fake a chosen method's evidence; project requirements remain binding. Every completed external `grill-with-docs` session invokes bundled `book-ddd-distilled-modeling` in all modes. For strict tasks, persisted/shared data, shared / persistent / cross-request / cross-process caches, async/cross-service flows, ownership, migrations, or recovery invoke `book-ddia-data-design`; existing-behavior bugs or uncertain existing code invoke `book-legacy-change-safety`; any existing-production-code edit invokes `book-refactoring-pass`; production-path runtime/deployment changes invoke `book-release-readiness` after all applicable testing-tool gates and project validation. Matched strict gates emit blocking visible statuses until passed; unmatched scenarios remain on demand.

Install every missing external Skill:

```bash
python scripts/onboard.py install-external-skills --all --scope global --source auto --yes
```

`--scope project` is rejected. Direct normal `init` and `reset` ensure every external Skill exists globally before template writes; the root installers perform the same guarantee before invoking the final mode.

Migrate all recognized legacy mattpocock directories in a specific global Skill root:

```bash
python scripts/onboard.py migrate-external-skills \
  --scope global \
  --source auto \
  --global-skills-dir /path/to/global/skills \
  --yes
```

Source policies:

- `auto` (default): require and validate the reviewed vendored stable manifest, checksum, frontmatter, and complete Skill tree without accessing Git or the network.
- `upstream`: explicitly opt into cloning and validating the current upstream repository group; any acquisition or validation failure is fatal and does not fall back.
- `stable`: use the same deterministic vendored source as `auto`, while recording explicit stable-source intent in `requestedSource`.

Preparation and commit are separate phases. Every selected Skill is resolved, copied into target-filesystem staging, and verified before any canonical or legacy target changes. Manifest paths, configured upstream subpaths, and license paths must remain relative to and contained by their declared roots; absolute paths, `..` traversal, and symlink escapes are rejected. Commit moves existing targets into a temporary rollback directory, installs every staged canonical target, and only then removes legacy aliases.

No automatic source fallback occurs. Stable manifest, containment, checksum, license, or snapshot validation failures are fatal for `auto` and `stable`; upstream acquisition or validation failures are fatal for `upstream`. Target-side staging, permission, disk, commit, and rollback failures are always fatal. A local commit failure attempts to restore all prior targets; if any restore step fails, the transaction reports and retains the rollback directory path instead of deleting the only remaining backup copy.

`init` / `reset --json` embed the required installation report under `requiredExternalInstall` in the single root document, including when installation fails before template writes. Per-Skill source metadata and `transaction` recovery fields remain available; the field is `null` when no required installation ran. Existing root plan fields and exit-code semantics are unchanged.

The vendored stable set lives at `assets/external-skills/stable/`. Its `MANIFEST.json` is the single source of truth for stable-set id, upstream repository, full commit SHA, upstream subpath, local stable path, tree SHA-256, and license/NOTICE files. The snapshots are upstream content copied unchanged. Do not hand-edit them.

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

First-time registration of a repository that is not yet in the manifest uses catalog-driven selection:

```bash
python scripts/onboard.py promote-external-skills-stable \
  --repository <new-repository-id> \
  --repo <upstream-https-url> \
  --revision <full-40-character-commit-sha> \
  --stable-set <yyyy-mm-dd.index> \
  --license <spdx-license-id> \
  --license-file "LICENSE=licenses/<new-repository-id>-LICENSE" \
  --yes
```

`--repo` must be a valid HTTPS URL and selects every catalog external entry whose `source.repo` matches it exactly; an empty selection is rejected. `--license` takes an SPDX id, and `--license-file` is repeatable with `SOURCE=STABLE_PATH` mappings. The current manifest is read in relaxed mode for this bootstrap, and catalog equality is enforced only after the candidate tree is fully assembled and validated. For an existing repository, `--repo` may only repeat the recorded URL and `--license` / `--license-file` are rejected, so promotion never silently rewrites repository metadata. Any validation failure leaves the live stable tree unchanged; if commit and rollback both fail, the single recovery directory is retained and reported.

Legacy aliases remain recognized for migration: `diagnose` → `diagnosing-bugs`, `write-a-skill` and `writing-great-skills` → `writing-for-agents`, `to-prd` → `to-spec`, and `to-issues` → `to-tickets`; removed `zoom-out` has no replacement. `migrate-external-skills` first validates every detected legacy target's directory and `SKILL.md` frontmatter identity. If any identity conflicts, it fail-closes before any canonical install, backup, or deletion. It then installs every required canonical replacement using the chosen source policy and shared transaction. When that transaction commits, its legacy predecessors and temporary rollback directory are deleted; the rollback directory is retained only for an incomplete restore. A legacy-only cleanup that needs no canonical install—because the canonical target is already valid or because the legacy target is `zoom-out`—copies the verified legacy directory into a persistent migration backup before removal. Normal `init` / `reset` retain legacy-only automatic migration so already canonical external Skills are not cloned twice during every run.

## Skills That Keep Their Existing Scope

- `caveman`: user-level global and still requires its existing explicit installation decision when missing. Replacement and backup cover only `caveman`, `caveman-*`, `cavecrew`, and `cavecrew-*`; broader `caveman*` / `cavecrew*` prefix matching is detection-only for the fail-closed symlink guard, which also covers nested symlinks at any depth inside an abnormal core. A known version requires the complete mutable family directory set and payload fingerprints to match a reviewed snapshot, using the existing generated-cache exclusions. Matching the core alone never authorizes replacement: partial, mixed, or customized payloads are reported as unknown drift, and an abnormal core cannot authorize replacing unrecognized companions. The staged source must match the pinned full family, and the live target is rechecked before replacement. Known older payloads are backed up before upgrade; replaceable non-symlink abnormal cores may be repaired when no unknown companion exists. Human `plan`, `install-caveman`, `init`, and `reset` reports include refusal reasons, retained backup paths, and restore errors. Caveman maintenance remains optional and does not turn a successful required installation into failure. Hooks, statusline, plugins, and extensions remain user-managed. Monitoring only reports drift; changing the maintenance baseline requires reviewing the complete family and installer / hook behavior and updating ref, revision, core hash, family fingerprints, and tests together. The external Skill owns manual style and intensity; the global AGENTS template owns automatic lifecycle with a monotonic eligibility latch. Only a new primary goal resets it, and protected replies preserve automatic state.
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
- Paid: require an existing entitlement and readable `REACTBITS_LICENSE_KEY`; never print or persist it. When prerequisites pass, add `@reactbits-starter/skill` from the project root with `--path .agents/skills/react-bits-pro --overwrite --yes`, then require `.agents/skills/react-bits-pro/SKILL.md` to exist. An existing target is overwritten without a backup.
- Reset: preserve the detected tier and registry.

## Multi-Project SBTD Setup

`check` / `check-projects` inspect selected state and scaffold conflicts read-only; `plan` exposes the same result in `sbtdInit`. `check-projects --skip-project-agents` excludes that unselected write target without skipping ignore/state checks. Missing optional state is valid and does not prove installation or create files.

The inspector validates the current active pointer and its selected task, plus `ai/tasks/00-bootstrap-guidelines/task.md` when explicitly present. It uses the bundled task v1 schema, safe JSON-compatible YAML, duplicate/cycle/nonfinite rejection, real timestamp parsing, filesystem containment and pointer/record logical-ID agreement. It does not scan history, infer a newest task, modify state, validate full parent/event history, or authorize branch recovery.

An unfinished bootstrap record reports `bootstrap-required`; no bootstrap is created by installation. A done record reports recorded completion only. Legacy `.trellis` yields `needs-user` for explicit migration and stays untouched. Malformed state is `blocked`. Every root retains `status`, `reason` and `nextStep`.

Both root installers gate all global/optional project mutations on the complete selected-project preflight; Python repeats it before its own installation writes. Reject blocking state, nonregular selected AGENTS/ignore targets, a multiply-linked ignore file, or new rules hiding existing unconfirmed reserved data. All roots retain results and a conflict stops the batch; reset preserves optional data. Read-only Agent detection may precede this gate, but installation/MCP writes may not.

Aggregate priority is `failed > blocked > needs-user > bootstrap-required > success > skipped`; exit codes remain 5, 2, 2, 6, 0, 0 respectively. A read-only plan may successfully report a blocked proposed operation without executing it.

## MCP Setup

MCP configuration remains optional and interactive in normal mode. Project-only mode skips it.

Built-in choices:

- Chrome DevTools MCP: `npx -y chrome-devtools-mcp@latest`
- Playwright MCP: when the selected Playwright distribution exposes it, use its bundled `npx playwright mcp` entrypoint; otherwise configure a compatible dedicated Playwright MCP server.
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

Additional OMP global AGENTS, only when the user-home `.omp` directory already exists:

- POSIX: `~/.omp/agent/AGENTS.md`
- Windows: `%USERPROFILE%\.omp\agent\AGENTS.md`

Existing OMP `AGENTS.md` is backed up then overwritten. Missing `.omp` is skipped; Onboard does not create `.omp`. `--global-agents-path` does not disable this extra write. If `--global-agents-path` or a project `AGENTS.md` resolves to the same file as the OMP or Codex global target, `init` / `reset` keep a single file write and a single backup.



Global Skills:

1. `--global-skills-dir`
2. `$AGENT_SKILLS_DIR`
3. Parent directory of an installed `sbtd-workflow-onboard` under `~/.agents/skills`, `~/.agent/skills`, `~/.codex/skills`, `~/.claude/skills`, `~/.pi/agent/skills`, or `$CODEX_HOME/skills`
4. `$CODEX_HOME/skills`
5. `~/.codex/skills`

Project paths, repeated for every selected root:

- `<project-root>/AGENTS.md`
- `<project-root>/.gitignore`
- optional `.sbtd/active-task.json` and its selected task (read-only)
- optional `ai/tasks/00-bootstrap-guidelines/task.md` (read-only)
- conditional project Playwright dependencies/configuration
- conditional React Bits Skill/registry

Generic bundled/external workflow Skills are never installed under `<project-root>/.agent/skills` by this onboard flow.

## Shared Python Commands

```bash
python scripts/onboard.py check --projects-root /abs/one,/abs/two
python scripts/onboard.py check-projects --projects-root /abs/one,/abs/two
python scripts/onboard.py plan --platform codex --projects-root /abs/one,/abs/two --json
python scripts/onboard.py init --platform codex --projects-root /abs/one,/abs/two --yes
python scripts/onboard.py reset --platform codex --projects-root /abs/one,/abs/two --yes
python scripts/onboard.py init-projects --platform codex --projects-root /abs/one,/abs/two --yes
```

`--json` emits one stdout JSON document; diagnostics use stderr. Write modes merge plan and results, including `sbtdInit`, `sbtdProjectSetup`, `backups` and `unverifiedChecks` as applicable. Project checks expose `sbtd`, not `trellis`. Removed setup fields have no aliases. Bootstrap/invalid-state results are nonzero; argparse syntax errors retain stderr and exit 2.

Global-only onboarding is still supported by omitting `--projects-root` and explicitly skipping project AGENTS when using the Python command directly:

```bash
python scripts/onboard.py init --platform codex --skip-project-agents --yes
```

## Verification

After writes:

1. Verify every copied AGENTS file against its source template.
2. Verify every bundled global Skill directory recursively.
3. Verify the project `.gitignore` block exists in every selected root.
4. Report per-root SBTD state/bootstrap results without claiming task recovery or acceptance proof.
5. Report per-root Playwright and React Bits decisions without claiming optional installation succeeded unless the command and post-check pass.
6. Rerun the target Agent CLI and global preflight after normal onboarding.
7. Rerun only `check-projects` after project-only onboarding.

Network, permissions, missing dependencies, unsupported platform execution, malformed state, legacy migration requirements and bootstrap-required results remain explicit; no skipped check is a pass.
