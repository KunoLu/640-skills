---
name: sbtd-workflow-onboard
description: Checks, installs, or resets SBTD workflow tools, global Skills, AGENTS templates, and per-project configuration for one or more local project roots.
---

# SBTD Workflow Onboard Skills

Use this Skill to onboard a local machine and initialize one or more projects with the SBTD workflow templates bundled under `templates/`.

The repository root installers are `install.sh` and `install.ps1`. `scripts/onboard.py` implements checks, plans, template writes, global Skill installation, and read-only per-project SBTD state/bootstrap checks.

The directory remains self-contained: `catalog.json` is the machine-readable source catalog, `catalog.schema.json` is its Draft 2020-12 contract, `scripts/` is the Onboard implementation, `templates/` is the install payload, and `assets/` contains managed third-party fallback snapshots. Keep this separation when adding catalog entries; do not move install payloads beside runtime code merely to flatten paths.

## Staged v2 Delivery (Unreleased)

This unreleased branch carries the v2 canonical payload (14 bundled Skills, with `sbtd-task` replacing `trellis-workflow` / `trellis-channel`; 19 required external Skills). Project setup no longer installs or invokes Trellis. Full Graft/host integration, task operations, identity creation and legacy migration remain staged P1 work; do not deploy this development branch as a completed v2 release. Existing legacy data is preserved and requires an explicitly authorized migration. P1-13 owns retirement of user-global legacy resources.

P1-01 supplies internal, directly callable argument and exchange-contract modules (`scripts/onboard_arguments.py`, `scripts/onboard_contracts.py`, `onboard-contracts.schema.json`). It does not activate new migration/recovery commands or deployment handlers in the existing CLI. Do not substitute contract fixtures, valid hashes, or a copied directory for executed migration or recovery evidence.

Whole-directory installation and `npx skills add` do not run pip. Before validating exchange contracts or existing task state, use the actual installed-copy interpreter: `python -m pip install -r /path/to/installed/sbtd-workflow-onboard/requirements.txt`. This declares jsonschema and PyYAML; missing dependencies block the affected validation without breaking help or pure argument parsing. Verify a fresh installed copy, not the source machine's existing packages.

Do not install the source repository root `AGENTS.md`, `ENTRYPOINT.md`, `README.html`, `archive/`, or `docs/lessons.md` as target templates.

## Required Questions

Resolve these questions in order:

1. Which target Agent platform is being configured: `codex`, `claude`, `kimi`, or `oh-my-pi` / `omp`?
2. Is this a normal `init` / `reset`, or project-only initialization equivalent to `--init-projects`?
3. What are the project roots? Accept one or more existing absolute paths separated by English commas.
4. Should project `AGENTS.md` be installed into every selected project root?

The Agent platform selects the CLI and MCP adapter; it does not select the global AGENTS target. Unless the user explicitly supplies a global AGENTS path, normal onboarding writes the Codex global template to the resolved `$CODEX_HOME/AGENTS.md` / `~/.codex/AGENTS.md` path. If the user-home `.omp` directory already exists (POSIX `~/.omp`, Windows `%USERPROFILE%\.omp`), `init` / `reset` also backup-then-overwrite the same template to `~/.omp/agent/AGENTS.md`. Missing `.omp` is skipped; Onboard does not create `.omp`. `--global-agents-path` overrides only the Codex target and does not cancel the OMP write. If that path or a project `AGENTS.md` resolves to the same file as another AGENTS target, Onboard keeps a single file write. Project-only mode does not write any global AGENTS file.

If multiple paths are supplied to this Skill but the user did not explicitly say they are projects to initialize, ask whether they are the intended initialization roots before running checks or writes. Do not infer that every mentioned repository path should be initialized.

Normal `init` / `reset` always target bundled and required external workflow Skills globally. There is no global/project/none Skill scope choice. `init` skips a bundled or required external Skill whose target is already a valid Skill shell (regular directory, regular `SKILL.md`, matching frontmatter `name`); installing a missing required external Skill does not reinstall already-valid dependencies. `reset` overwrites every bundled Skill without backup and force-reinstalls every required external Skill from the current stable snapshot. Global and project `AGENTS.md` still backup-then-overwrite; project `.gitignore` still appends missing template lines. Project-only initialization must not check, install, update, or configure global Agent CLIs, runtimes, tools, Skills, AGENTS, or MCP.



## Skill Installation Modes

The official `skills` CLI may install this self-contained directory as the bootstrap Skill without cloning the whole repository first:

```bash
npx --yes skills@latest add \
  https://github.com/KunoLu/640-skills \
  --skill sbtd-workflow-onboard \
  --global \
  --agent codex \
  --yes \
  --copy
```

The `npx skills add` command installs only the `sbtd-workflow-onboard` package. It does not execute `scripts/onboard.py`, install Trellis or GitNexus, write AGENTS files, install the other bundled/external Skills, or initialize a project. After installation, invoke this Skill through the Agent and run `scripts/onboard.py plan --json`, `init`, or `reset` as required.


The repository root `install.sh` and `install.ps1` remain the complete interactive entrypoints when the repository is already cloned. Do not duplicate `templates/skills/**` at the repository root or add a second bootstrap Skill to accommodate the `skills` CLI; the top-level `SKILL.md` is the single discovery entrypoint.

## Root Installer Interfaces

Normal onboarding:

```bash
bash install.sh \
  --platform codex \
  --projects-root /abs/project-one,/abs/project-two \
  --action init
```

```powershell
.\install.ps1 \
  -Platform codex \
  -ProjectsRoot "C:\work\one,C:\work\two" \
  -Action init
```

Project-only initialization:

```bash
bash install.sh \
  --platform codex \
  --init-projects /abs/project-one,/abs/project-two
```

```powershell
.\install.ps1 \
  -Platform codex \
  -InitProjects "C:\work\one,C:\work\two"
```

`--projects-root` / `-ProjectsRoot` and `--init-projects` / `-InitProjects` are mutually exclusive. Every path must be absolute and must already be a directory. Duplicate paths are normalized and processed once.

When normal onboarding omits the `projects-root` argument, explain that multiple absolute paths are supported with English commas, ask whether the current working directory is a target project, and otherwise prompt for the comma-separated list. A blank answer means global-only onboarding.

## Target Agent CLI Gate

Normal onboarding resolves the Agent first and may inspect its CLI before the remaining questions. Collect all project roots and the project-AGENTS choice, then run the complete read-only `check-projects` preflight before any Agent/runtime/Skill installation, MCP write, or optional project installation. Pass `--skip-project-agents` when that target was explicitly excluded. Recheck immediately before Python writes.

| Platform | Verify | Required global npm package when missing |
|---|---|---|
| `codex` | `codex --version` | `@openai/codex@latest` |
| `claude` | `claude --version` | `@anthropic-ai/claude-code@latest` |
| `kimi` | `kimi --version` | `@moonshot-ai/kimi-code@latest` |
| `oh-my-pi` / `omp` | `omp --version` | `@oh-my-pi/pi-coding-agent@latest` |

After the selected-project preflight passes, repair a missing/broken target CLI through the existing npm gate and require its version check to pass. The remaining transitional GitNexus tool also requires npm; Graft replacement is separate staged work.

Project-only `--init-projects` asks for or accepts the platform but skips this Agent CLI/npm gate and every other global preflight.

## Mandatory Global Installation Policy

Normal `init` and `reset` require these global tools:

- GitNexus CLI: `npm install -g gitnexus@latest`

Project-local GitNexus CLI installation is not supported by the transitional installer. Existing `.trellis/` is preserved for explicit migration; Onboard neither installs nor invokes Trellis.

All bundled Skills install globally as one required set:

- `sbtd-workflow-onboard`
- `sbtd-task`
- `project-validation`
- `web-ui-autotest-generator`
- `gherkin-bdd`
- `knowledge-base-integration`
- `maestro-mobile-e2e`
- `lessons-record`
- `book-refactoring-pass`
- `book-legacy-change-safety`
- `book-ddd-distilled-modeling`
- `book-ddia-data-design`
- `book-release-readiness`
- `seo-geo`

After the canonical `sbtd-workflow-onboard` target is written and its `SKILL.md` frontmatter validates, remove a legacy `kuno-workflow-onboard-skills` target only when that directory's own `SKILL.md` frontmatter still identifies it as `kuno-workflow-onboard-skills`. A conflicting file, unrelated directory, or mismatched frontmatter blocks `init` / `reset` before any target changes and remains untouched; deletion errors are reported as migration failures. This is a clean rename migration, not an alias: never retain both directories after a successful normal `init` or `reset`.

All referenced external Skills are also required globally. Install every missing item without a scope or selection prompt:

- `diagnosing-bugs`, `tdd`, `grill-me`, `grill-with-docs`, `grilling`
- `domain-modeling`, `codebase-design`, `handoff`, `writing-for-agents`
- `to-spec`, `to-tickets`, `ui-ux-pro-max`, `impeccable`
- `shadcn`
- `ponytail`, `ponytail-review`, `ponytail-audit`, `ponytail-debt`
- `i-have-adhd`

Dependencies are still expanded automatically: `tdd` includes `codebase-design`; `grill-me` includes `grilling`; `grill-with-docs` includes `grilling` and `domain-modeling`.

The four Ponytail Skills are required like every other external Skill: `check` only inspects and reports them, while normal `init` / `reset` installs or repairs missing and invalid copies from the vendored stable set without asking, and a failed install fails the run. Onboard uses the stable skill-only provider and never installs, enables, disables, trusts, or removes the official Ponytail plugin. When `check` detects the official Ponytail plugin enabled for Codex or OMP, it reports `ponytailProvider.provider=conflict` and fails; `init` / `reset` block before writing stable copies, and the root installers stop with the same guidance. A plugin that is installed but disabled is reported but does not block. `ponytail-gain` and `ponytail-help` belong only to the official plugin and are never managed by Onboard.

The mandatory runtime gate contracts are owned by the installed global `AGENTS.md`, project template, bundled `sbtd-task`, and bundled reviewer Skills. They become active only after normal `init` / `reset` successfully writes the global rules and installs the required bundled / external Skills. The public Skills CLI bootstrap and `init-projects` do not activate these runtime gates by themselves; they only install the Onboard Skill or process project-local assets respectively.

At runtime, a `strict` development task first produces a `Book Gate Plan` with objective predicates and lifecycle states. `default` / `lite` tasks select methods by actual risk and explicit deliverables and never fake a chosen method's evidence; project requirements remain binding. Every completed external `grill-with-docs` session invokes bundled `book-ddd-distilled-modeling` in all modes. For strict tasks, persisted/shared data, shared / persistent / cross-request / cross-process caches, async/cross-service flows, ownership, migrations, or recovery invoke `book-ddia-data-design`; existing-behavior bugs or uncertain existing code invoke `book-legacy-change-safety`; any existing-production-code edit invokes `book-refactoring-pass`; production-path runtime/deployment changes invoke `book-release-readiness` after all applicable testing-tool gates and project validation. Matched strict gates block their phase until passed; unmatched scenarios remain on demand.

External Skill installation uses a validated, stable-first source policy. The default `auto` policy and explicit `stable` policy both resolve every selected Skill from the reviewed vendored set under `assets/external-skills/stable/` without accessing Git or the network. Only explicit `upstream` opts into cloning and validating the current upstream repository group, and upstream failure does not fall back. Manifest, source-subpath, and license paths must stay contained by their declared roots. All selected Skills are staged before any target changes, and target replacement uses a temporary rollback transaction. Source-integrity and target-filesystem failures are fatal; an incomplete restore retains and reports the rollback directory.

The stable set is an unmodified mirror, not a fork. `assets/external-skills/stable/MANIFEST.json` records the exact upstream commit, source subpath, tree digest, and license files. Promote a new repository revision only through `promote-external-skills-stable`; promotion must validate the complete stable set before replacing it.

`caveman` remains a user-level global Skill with its existing explicit installation decision. Normal `init` / `reset` preserves a missing copy, but maintains an installed workflow skill payload against the reviewed pinned v* installer / skill baseline: known older payloads are backed up then upgraded, replaceable non-symlink abnormal payloads are repaired, symlinked payloads fail closed and are reported, and newer or customized payloads are reported without replacement. This scope is `caveman*` / `cavecrew*` Skills only; hooks, statusline, plugins, and extensions remain user-managed. ENTRYPOINT monitoring only reports v* tag drift; a human-reviewed change must update the pinned ref, revision, hashes, and tests together. Java 17+ and Maestro CLI remain local-machine prerequisites installed only after their existing conditional confirmation. RTK remains global with its existing confirmation and `rtk gain` verification behavior.

## Per-Project Processing

For every selected root, inspect SBTD state before installation writes. A missing `.sbtd`, identity, task or bootstrap is normal; ordinary work does not require onboarding.

1. Validate only the active bookmark/selected task and an existing `ai/tasks/00-bootstrap-guidelines/task.md`: safe UTF-8 JSON/YAML, bundled v1 schema, real dates, path types/containment and full logical-ID agreement. This is not full event/parent/branch recovery validation.
2. Report malformed state as blocked, legacy `.trellis` as needs-user for migration, and an explicitly present unfinished bootstrap as bootstrap-required. A done record is recorded state, not independent acceptance evidence. Inspect all selected roots; any blocking result stops installation writes for the batch.
3. Reject unsafe AGENTS/ignore destinations and newly hiding existing reserved data. Resolve ownership/protection explicitly rather than silently adding ignore coverage.
4. Install selected project AGENTS and append missing project `.gitignore` lines without reordering existing content. Preserve task, identity, spec, lessons, handoff and legacy data. Do not create those optional artifacts.
5. Check applicable project-local Playwright and React Bits conditions; retain their existing installation confirmations.

Playwright CLI remains project-only and is installed with `install-playwright-cli --project-root <one-root> --yes` after confirmation.

React Bits remains project-only and optional:

- shadcn/ui-only is the default choice.
- React Bits Free requires an explicitly configured free registry item.
- Paid Starter / Pro / Ultimate setup requires an existing entitlement and a readable `REACTBITS_LICENSE_KEY`; install the Skill at `.agents/skills/react-bits-pro/SKILL.md`, overwriting that target without a backup, and never print or persist the key.
- Preserve a detected tier/registry during reset.

## MCP Scope Policy

MCP selection remains interactive and is skipped entirely in project-only mode. The built-in choices remain Chrome DevTools MCP, Playwright MCP, Maestro MCP, GitNexus MCP, and custom stdio MCP.

The target scope is fixed by Agent platform:

- Codex: user-level `codex mcp add` behavior.
- Claude Code: always `--scope user`.
- Kimi Code: keep the CLI default behavior; do not add a scope flag.
- Oh My Pi: always write the global `~/.omp/agent/mcp.json` file.

Do not couple MCP scope to project roots or Skill scope. Do not configure project-level Claude or Oh My Pi MCP entries during onboarding.

## Shared Python Commands

Global and multi-project check:

```bash
python scripts/onboard.py check \
  --projects-root /abs/project-one,/abs/project-two
```

Project-only check without global runtime/tool/Skill inspection:

```bash
python scripts/onboard.py check-projects \
  --projects-root /abs/project-one,/abs/project-two
```

Normal plan/init/reset:

```bash
python scripts/onboard.py plan --platform codex --projects-root /abs/one,/abs/two --json
python scripts/onboard.py init --platform codex --projects-root /abs/one,/abs/two --yes
python scripts/onboard.py reset --platform codex --projects-root /abs/one,/abs/two --yes
```

Project-only initialization:

```bash
python scripts/onboard.py init-projects \
  --platform codex \
  --projects-root /abs/one,/abs/two \
  --yes
```

External Skill installation accepts global scope only:

```bash
python scripts/onboard.py install-external-skills --all --scope global --yes
```

Choose an explicit source policy when needed:

```bash
python scripts/onboard.py install-external-skills --all --scope global --source upstream --yes
python scripts/onboard.py install-external-skills --all --scope global --source stable --yes
```

Migrate every recognized mattpocock legacy directory in a global Skill root:

```bash
python scripts/onboard.py migrate-external-skills --scope global --source auto --yes
```

The migration validates each legacy `SKILL.md` identity before it changes any target, installs required canonical replacements transactionally, and then removes the verified legacy directories.

Promote a reviewed upstream repository revision into a new stable set:

```bash
python scripts/onboard.py promote-external-skills-stable \
  --repository mattpocock-skills \
  --revision <full-commit-sha> \
  --stable-set <yyyy-mm-dd.index> \
  --yes
```

First-time registration of a repository that is not yet in the stable manifest additionally requires `--repo`, `--license`, and at least one `--license-file SOURCE=STABLE_PATH` mapping; the promoted Skills are selected from catalog external entries whose `source.repo` matches `--repo` exactly. For a repository that already exists in the manifest, `--repo` may only repeat the recorded URL and `--license` / `--license-file` are rejected, so promotion can never silently rewrite repository metadata.

## Reporting

Normal `check`, `init`, and `reset` report global runtime/tools/Skills plus a `projectChecks` entry for every selected root. `check-projects` and `init-projects` report only project-local checks and writes.

Aggregate SBTD status priority is `failed`, `blocked`, `needs-user`, `bootstrap-required`, `success`, `skipped`. All selected roots retain individual status/reason/nextStep. Blocking preflight stops the whole installation batch before template or Skill writes.

Every External Skill install result must report `requestedSource`, `sourceUsed`, `sourceRevision`, `stableSet`, `fallbackReason`, and transaction status when applicable. Every project result must identify the affected project root. Do not merge failures, bootstrap tasks, Playwright applicability, or React Bits decisions across projects without preserving the root path.

`init` / `reset --json` keep one root document. When required external installation runs, `requiredExternalInstall` contains its complete result, including per-Skill provenance and `transaction.rollbackPath` / `rollbackErrors` on failed recovery; it is `null` when installation was unnecessary. Preserve this result on early failure returns as well as successful runs. Human Caveman reports include refusal reasons, retained backup paths, and restore errors.

See [REFERENCE.md](REFERENCE.md) for exact overwrite, backup, troubleshooting, and platform details.
