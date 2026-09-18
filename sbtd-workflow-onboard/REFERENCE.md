# SBTD Workflow Onboard Reference

## Bundled Templates

- `templates/agents/AGENTS.global.md` -> global Codex `AGENTS.md`, and `~/.omp/agent/AGENTS.md` when `~/.omp` already exists
- `templates/agents/AGENTS.project.md` → each selected project root `AGENTS.md`
- `templates/project/.gitignore` → each selected project root `.gitignore`
- `templates/skills/**` → required global bundled Skills

`catalog.json` is the runtime source of truth for these paths, all bundled Skill ids, and every external Skill repository/subpath/alias. `catalog.schema.json` defines its Draft 2020-12 contract; `examples/catalog.minimal.json` is the minimal valid shape. The root installers require both catalog files, and `scripts/onboard.py` rejects duplicate ids, absolute or escaping paths, malformed HTTPS repository URLs, invalid kind/id/target-role combinations, wrong local source types, missing sources, and bundled Skill frontmatter identity mismatches before processing a command.

> **Staged v2 delivery (unreleased):** canonical payload is 14 bundled / 19 external Skills. Project setup now uses read-only SBTD checks without Trellis installation or initialization. Graft/host integration, task operations and legacy migration remain staged work; on-demand identity creation is now provided by the P1-19 `DeveloperStore` and the explicit `--developer` entry described below. This is not a completed v2 release. Existing legacy data is preserved; user-global retirement remains P1-13.

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
5. Offers Graft's pinned global installation after showing its plan; refusal does not install npm/Graft or block unrelated safe work.
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
3. Skips global Agent/runtime/tool/Skill/AGENTS/MCP detection and installation, including Graft and HOME telemetry configuration.
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

Graft is an explicitly confirmed auxiliary CLI, pinned to `@nanonets/graft@0.18.0` with Node >=20. Existing local availability is checked independently of npm or latest-version reachability. No automatic upgrade, install loop or offline-mirror product is provided.

```bash
python scripts/onboard.py install-graft --json
python scripts/onboard.py install-graft --yes --json
```

Without confirmation the handler only reports its package/prefix/telemetry plan. The confirmed path verifies frozen tarball integrity, enables the required native lifecycle scripts, installs at the configured npm global prefix, verifies the installed pinned CLI and atomically persists `~/.graft/telemetry.json` with `enabled=false`. Unknown JSON fields and existing data are preserved; unsafe paths, malformed state or failed readback remain failures, not success.

All managed Graft children receive `DO_NOT_TRACK=1`, an empty dotenv input and no inherited LLM/cloud activation settings. The installation child also uses `CI=1` to avoid this pin's detached postinstall path; runtime DNT is separately exercised without relying on CI. These child settings do not edit the user's global environment.

`graft --version` is local-only; `graft version` invokes npm metadata and can return an offline/unreachable message. Check/plan never run the latter. A cached npm answer is not proof of connectivity; offline verification uses a real network control and empty per-case caches.

GitNexus installation and dedicated MCP suggestions are removed. Existing user GitNexus resources are left untouched; Graft graph/host/MCP integration is a separate later stage.

RTK remains optional and retains its confirmation flow. Onboard verifies the binary with an isolated `gain` probe, because running it in an empty user HOME creates a history database. `verificationScope=isolated-probe` means actual user-history directory permissions and contents were not verified. Do not interpret probe success as a repair of the user's data directory.

## npm and nvm

Installing a missing selected Agent or an explicitly accepted npm-backed tool requires npm. A working local Graft/Agent is not blocked just because npm/latest lookup is absent. On macOS and Linux, prerequisite installation remains explicit:

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

## Task State Library (P1-17)

`scripts/sbtd_task_document.py` and `scripts/sbtd_task_state.py` are a host-native Python library shipped with the installed Onboard Skill. They are not `onboard.py` subcommands and do not register a new global CLI, daemon, journal, or background service. Markdown structure recognition uses the declared dependency markdown-it-py>=4,<5 (CommonMark tokens, parse-only, no rendering, no network; Python >=3.10). When the installed helper copy or its declared dependencies (PyYAML, jsonschema, markdown-it-py) are missing, parsing and task-state writes stop explicitly; callers must report that persistence did not run rather than claiming it.

The task document owns mode, status, timestamps and the single `## 状态事件` table; `.sbtd/active-task.json` is only a bookmark. `TaskDocument.parse` / `updated` preserve frontmatter extensions, body and attachments that do not belong to the current operation.

`TaskStore(root, read_only=False)` public operations:

- `inspect(task_id=None)` — read-only; without an id it resolves the active bookmark and checks it against the logical record.
- `create(task_id, body=..., mode=None, mode_note=None, parent=None, shared=False, confirmed=False)`
- `select(task_id, confirmed=False)`
- `transition(task_id, status, reason=..., evidence=..., confirmed=False)`
- `set_mode(task_id, mode, note=..., confirmed=False)`
- `resume(task_id, reason=..., evidence=..., target=None, confirmed=False)`
- `reopen(task_id, reason=..., evidence=..., confirmed=False)`
- `protect_local_state(confirmed=False)` — first-time narrow protection appends only `/.sbtd/` to the project `.gitignore`.
- `promote(task_id, confirmed=False, retire_source=False, include_tasks=())`
- `archive(task_id, reason=..., evidence=..., confirmed=False, retire_source=False, include_tasks=())`
- `current_binding()` — read-only; the actual branch, `detached:<full-sha>`, or `None` for a proven non-Git root.
- `recovery_candidates(task_id=None)` — read-only; the explicit task, the valid active bookmark, or every recorded candidate, never an mtime pick.
- `rebind(task_id, expected_branch=..., reason=..., evidence=..., confirmed=False)` — the only write path that changes a branch binding; records a same-phase event with the old and new binding and never checks out, stashes, or resets blocked recovery history.

Unconfirmed calls only report the planned result without writing. `promote` / `archive` return `TaskTransfer(status, task, source_path, target_path, files, retained_original, completed_steps)`; failures report `reason`, `next_step` and the actual `completed_steps`. Engineering boundaries:

- New tasks default to local `.sbtd/tasks/<id>/task.md`; lite/strict or explicit sharing uses `ai/tasks/<id>/task.md`. Mode and storage are orthogonal. Git projects bind the actual branch or `detached:<full-sha>`; non-Git projects record `branch=null`.
- Promotion/archive are two-phase: the first confirmed call prepares and verifies the complete target candidate, the effective active reference and the necessary shared index; `retire_source=True` requires an already prepared target plus a separate confirmation, then atomically moves the original directory into `.sbtd/task-originals/<generated>/task`. Originals are retained, never recursively deleted.
- Candidate copies live only in the protected `.sbtd/task-transfer-candidates/` area owned by the current operation and are cleaned up afterwards; they are not a second valid task record, and no journal service exists beside the task document.
- Other logical `task.md` records inside a task directory must each be authorized via `include_tasks`; path nesting is not ownership.
- Unknown or conflicting blocked history requires an explicit user phase choice; no ingress is fabricated and a blocked task never returns directly to done.
- Retries reconcile against recorded state and events instead of appending duplicate completion or release events.
- Windows support, host routing and legacy migration remain later stages; on-demand identity creation is covered by the P1-19 section below. Full validation, real-host proof and release are not claimed here.

## Routing and Handoff Helpers (P1-18)

`scripts/sbtd_task_routing.py` and `scripts/sbtd_handoff.py` extend the same host-native library; they register no global CLI, daemon, journal, scheduler, or `onboard.py` subcommand and reuse the `TaskStore` parsing, protection checks and atomic writes instead of duplicating them.

`TaskRouter(store).route(RouteRequest(...))` maps only facts the host already made explicit to a deterministic `RouteDecision(status, mode, persisted, task, reason, candidates)`:

- `RouteRequest` carries `intent` (`new` / `continue` / `question`), optional `task_id`, `explicit_mode`, `read_only`, `confirmed`, `body`, `mode_note`, an optional `ModeRecommendation(mode, reason, risk_id)`, its `recommendation_response` (`accept` / `keep`) and the `refusal_reason`. The router never classifies natural language or infers intent.
- `continue` resolves exactly one task via `recovery_candidates` before any mode decision: multiple or missing candidates return `needs-task-choice` with the candidate IDs; an unresolved recorded mode returns `needs-mode-choice`; a branch mismatch returns `needs-branch-choice` (correct worktree, explicit `rebind`, or read-only). A task's valid record outranks any old handoff.
- A recommendation for a different mode first returns `needs-mode-decision` without writing or executing; `accept` applies the recommended mode, `keep` requires the user's refusal reason and records the refusal in a structured `mode_note` deduplicated by risk identity, so an unchanged risk is not re-prompted.
- Read-only requests, read-only stores and pure `question` intent return `ready` with the session-only choice and write nothing. A confirmed save that fails returns `persistence-failed`: the session choice stands, the old mode is not restored, and recovery is not claimed reliable. Without confirmation a changed choice returns `needs-persistence-confirmation`.

`HandoffStore(tasks)` persists continuation snapshots under the protected `docs/handoffs/` only:

- `HandoffPolicy(task_opt_out=False, session_opt_out=False)` carries the two independently latched opt-outs; the store never mutates it, and a session opt-out is reported before a task opt-out. `save(task_id, content=..., trigger=..., policy=..., confirmed=False, redaction_confirmed=False)` returns `HandoffResult(status, persisted, path=None, snapshot=None, reason=None)` with the full status set: `suppressed` (trigger outside the `pause` / `context-switch` / `branch-switch` / `context-pressure` / `manual` allowlist — status counts and entering checking included — or an automatic trigger hitting a latched opt-out; `manual` ignores opt-outs without clearing them), `conversation-only` (read-only store, even for `manual`; nothing is ever written), `branch-conflict` (task record branch differs from the current binding; zero writes and the recorded actual mode is preserved), `unprotected` (`docs/handoffs/` is not ignored; a tracked or unverifiable protection state raises `TaskStateError` instead), `unchanged` (an identical meaningful snapshot already exists — the comparison covers every field including status, mode, HEAD, policy and content and excludes only `created_at`, so a day crossing alone never rewrites; result is `persisted=True` with the existing path), `pending-confirmation` (`confirmed=False`; the planned snapshot is returned, nothing written), `needs-redaction` (confirmed without the explicit `redaction_confirmed`) and `saved`.
- `protect(confirmed=False)` returns True when it appended the root-anchored `/docs/handoffs/` rule and False when protection already exists; it raises `TaskStateError` for a read-only store, a missing confirmation, tracked state, or a rule that would hide unknown existing data. On a genuinely non-Git root the rule is inserted before a final `/.sbtd/` rule so both protections stay valid; it never initializes Git. Existing malformed or foreign files are rejected, never overwritten.
- File names are `docs/handoffs/{YYYY_mm_dd}-<hex>.md` where `<hex>` is the lowercase hex of the UTF-8 full logical task ID: collision-free (including case-differing IDs on case-insensitive filesystems), OS-safe and reversible; the file name alone is never authority. The snapshot frontmatter records `schema_version`, `task_id`, `task_path`, `task_status`, `workflow_mode`, `mode_source`, `mode_note`, `project_root`, `branch`, `head` (null for unborn HEAD / non-Git), `created_at`, `content`, `policy` and the fixed caller-reviewed `redaction` declaration. Content requires exactly the `goal` / `next_action` / `limitations` strings and the `decisions` / `completed` / `remaining` / `changed_files` / `verification` / `do_not_repeat` string lists, plus an optional JSON-compatible `presentation`; unknown keys are rejected.
- `load(relative_path)` strictly parses only owned snapshots: closed shape with `schema_version` 1, the filename hex must decode to the frontmatter `task_id`, and `project_root` must equal this root; malformed, unowned or foreign files raise `TaskStateError` and are never overwritten. Snapshots of any age load fine and never change the task. `reminders(now=None)` returns only snapshots at most seven days old, latest per task, whose root and current branch binding match and whose task is unfinished; malformed or foreign files are skipped and each returned dict adds its `path`. No automatic session-start claim is made without an observed host capability.

Whether the Agent truly recommends first and pauses, invokes grill/DDD, or executes a mode's full method remains owned by the Skill rules and real-host proof, not by these return values. Windows, host wiring, automatic session-start restoration and legacy migration remain unclaimed.

## Developer Identity (P1-19)

`scripts/sbtd_identity.py` implements the lessons identity chain as a host-native library; it registers no global CLI, daemon, initializer, or identity database, and reuses `TaskStore` containment, protection and atomic writes instead of duplicating them.

`DeveloperStore(root, read_only=False)` operations, each returning a frozen `IdentityResult(status, name, source, path, first_write_eligible, topology, reason, needs_protection, completed_steps)` (exportable via `dataclasses.asdict`):

- `resolve()` — read-only. A valid local `.sbtd/developer` (UTF-8, one unambiguous `name=` line whose value matches `^[a-z0-9]+$` verbatim) returns `ready` with `source="local"` and no Git call. Only when the local file is genuinely absent does it verify the real Git toplevel, the absolute git-dir/common-dir and the NUL-separated worktree registry; a verified linked worktree then reads the same-repo main checkout's current identity in place (`source="main-worktree"`), never copying it. Present-but-abnormal local or main files (duplicate declarations, invalid name, wrong type, symlink, unreadable, unsafe parents) return `conflict`, never missing; unknown or unavailable Git metadata returns `blocked`, never assumed non-linked. A verified absent chain returns `needs-name` with `first_write_eligible=True`.
- `plan(name)` — read-only. The same existing identity returns `unchanged`; a different existing identity returns `conflict`; a verified missing target returns `planned`, with `needs_protection` reporting whether the narrow `/.sbtd/` ignore rule is still missing. It downloads nothing, writes nothing and creates no task or spec.
- `ensure(name, confirmed=False, protect=False)` — writes only from a `planned` result: without confirmation it returns `needs-confirmation`; when the required ignore rule is missing and `protect` was not explicitly allowed it returns `needs-protection` (the presence of a name never implies protection authorization). Creation rechecks the chain, writes only `name=<name>\n` non-overwriting, and re-reads before reporting `created`; a concurrent winner is preserved, a same-name retry is `unchanged`, and any failure returns `failed` with the honest `completed_steps`.

`onboard.py` consumes identity only through an explicit `--developer <name>` (validated by the same `validate_developer_name`, accepted at most once):

- `check` / `plan --developer` stay read-only and add a `developerPlan` object to the single JSON document: `requestedName`, aggregate `status`, `reason`, and a `projects` list whose entries carry `projectRoot`, `requestedName`, `status`, `name`, `source` (`local` / `main-worktree` / null), `target` (the `.sbtd/developer` path), `topology`, `needsProtection`, `reason` and `completedSteps`. A conflict, blocked or needs-* aggregate, or an empty project scope, exits 2 — the name is never defaulted to cwd or HOME.
- `init` / `reset` / `init-projects` apply the name only to the explicitly listed projects together with `--yes`; the full-batch identity plan is checked before any global or project mutation, so an existing conflict is refused before side effects rather than after another project was written. A `planned` entry that still needs protection goes through the existing confirmed scaffold ignore flow first, then `ensure(confirmed=True)` re-verifies; identity ensure never replaces the whole initialization flow nor rewrites `TaskStore` protection. A post-write identity failure exits nonzero with the single JSON document preserving partial results. A same-name inherited main identity is `unchanged` with no local copy.
  Only an original plan entry with `needsProtection=true` forwards protection authorization to `ensure(protect=True)` after the user confirms that listed initialization scope. This lets a verified non-Git project complete the existing narrow final-root-rule safeguard; an unplanned new protection need remains unauthorized. The helper never initializes Git or broadens the project list.
- Once identity initialization follows completed scaffold writes, JSON retains their actual `operationResults`. Identity failure also reports post-write `sbtdProjectSetup`, `developerPlan`, backups and unverified checks in that same document; it does not imply rollback. A project root becoming unavailable is a per-project `blocked` preflight or `failed` write result, preserving earlier projects' completed results instead of aborting with a traceback.
- Without `--developer` nothing changes: no command creates, repairs or requires an identity, and `reset` preserves any existing file.

Ordinary resolve/plan/check/global installation never reads `.trellis/.developer`; authorized legacy identity migration remains the separately gated P1-12 task and is not claimed complete by this helper. The root installers (`install.sh` / `install.ps1`) gain no new flag here; full wrapper forwarding remains P1-07 / P1-08. Windows proof, host wiring, full validation and release remain unclaimed.

## MCP Setup

MCP configuration remains optional and interactive in normal mode. Project-only mode skips it.

Built-in choices:

- Chrome DevTools MCP: `npx -y chrome-devtools-mcp@latest`
- Playwright MCP: when the selected Playwright distribution exposes it, use its bundled `npx playwright mcp` entrypoint; otherwise configure a compatible dedicated Playwright MCP server.
- Maestro MCP: `maestro mcp` with `JAVA_HOME` and `PATH`
- Custom stdio MCP: user-provided command/args/env

Graft MCP is not advertised by this CLI-install slice; later host producers must prove their actual environment, ownership and handshake before adding it.

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
