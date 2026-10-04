# SBTD Workflow Onboard Reference

## Bundled Templates

- `templates/agents/AGENTS.global.md` -> global Codex `AGENTS.md`, and `~/.omp/agent/AGENTS.md` when `~/.omp` already exists
- `templates/agents/AGENTS.project.md` → each selected project root `AGENTS.md`
- `templates/project/.gitignore` → each selected project root `.gitignore`
- `templates/skills/**` → required global bundled Skills

`catalog.json` is the runtime source of truth for these paths, all bundled Skill ids, and every external Skill repository/subpath/alias. `catalog.schema.json` defines its Draft 2020-12 contract; `examples/catalog.minimal.json` is the minimal valid shape. The root installers require both catalog files, and `scripts/onboard.py` rejects duplicate ids, absolute or escaping paths, malformed HTTPS repository URLs, invalid kind/id/target-role combinations, wrong local source types, missing sources, and bundled Skill frontmatter identity mismatches before processing a command.

> **Staged v2 delivery (unreleased):** canonical payload is 14 bundled / 19 external Skills. Project setup uses SBTD checks without Trellis initialization. Graft detection/installation, explicit Codex/OMP project wiring, task libraries, developer identity, migration plan/apply/verify, cleanup/recovery and the corresponding root-installer forwarding have stage-owned implementations. Windows-native proof and full v2 release remain separately gated. Existing legacy data is preserved.

The P1-01 argument/codec modules and `onboard-contracts.schema.json` provide the exchange contracts. P1-12 exposes migration plan/apply/verify; P1-04/P1-05 supply Codex/OMP wiring and the migration-context deployment producer below; cleanup and recovery are implemented by their owning tasks. Contract validation checks declared structures and relationships; filesystem safety, authorization and actual operations remain stage-owned.

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
7. Without `--yes` / `-Yes`, a normal root-installer run that receives neither project argument asks whether cwd is a project root, explains the absolute CSV format, and otherwise prompts for the list.
8. A blank interactive project list means global-only onboarding.
9. With `--yes` / `-Yes`, normal `init` / `reset` without `projects-root` is global-only. It does not ask the cwd question or implicitly select cwd; project AGENTS/ignore/graph assets are not installed. Explicit `projects-root` and `init-projects` selections are unchanged.

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
3. Skips global installation and user configuration. Explicit Python Codex/OMP project setup may detect the already-installed fixed Graft/Node locally; it never installs them or writes HOME telemetry.
4. Runs complete read-only `check-projects` with the actual `--skip-project-agents` scope before any optional project install.
5. Offers only applicable project-local Playwright or React Bits decisions.
6. Writes project AGENTS and `.gitignore`.
7. Requires no Trellis CLI, developer name or pre-existing task state.
8. Reports an explicitly present unfinished SBTD bootstrap task without creating one.
9. For explicit Codex or OMP projects with fixed Graft available, maintains the project fence and graph; otherwise reports not-available and continues unrelated setup. No HOME, user-level MCP or hook writes.

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

Normal onboarding may probe the target CLI read-only first, but collects the action, project list and AGENTS scope and passes complete project preflight before any CLI installation or repair. Oh My Pi follows the requested npm path and is accepted only when `omp --version` succeeds.

## Required Global Tools

Graft is an explicitly confirmed auxiliary CLI, pinned to `@nanonets/graft@0.21.1` with Node >=20. Existing local availability is checked independently of npm or latest-version reachability. No automatic upgrade, install loop or offline-mirror product is provided.

```bash
python scripts/onboard.py install-graft --json
python scripts/onboard.py install-graft --yes --json
```

Without confirmation the handler only reports its package/prefix/telemetry plan. The confirmed path verifies frozen tarball integrity, enables the required native lifecycle scripts and verifies the installed pinned CLI. Telemetry persistence is create-only: an absent `~/.graft/telemetry.json` is atomically published without replacing a concurrent creator; an existing `enabled=false` file is read-only. Any existing file requiring an update blocks without mutation. Graft does not share a conditional-write protocol, so read/compare/replace cannot safely preserve concurrent updates. Resolve existing enabled state externally under exclusive control before retrying; the installer never invokes Graft's telemetry command or silently overwrites foreign fields.

When only telemetry opt-out is selected, use `install-graft --telemetry-only --yes --json`. The handler rechecks the verified pinned CLI and blocks if it disappeared or changed; it never falls through to npm/package installation under telemetry-only consent. Both root wrappers preserve this action boundary after showing the probe plan.

All managed Graft children receive `DO_NOT_TRACK=1`, an empty dotenv input, `DOTENV_CONFIG_QUIET=true`, and no inherited dotenv-debug or LLM/cloud activation settings. The installation child also uses `CI=1` to avoid this pin's detached postinstall path; runtime DNT is separately exercised without relying on CI. These child settings do not edit the user's global environment.

`graft --version` is local-only; `graft version` invokes npm metadata and can return an offline/unreachable message. Check/plan never run the latter. A cached npm answer is not proof of connectivity; offline verification uses a real network control and empty per-case caches.

GitNexus installation and dedicated MCP suggestions are removed. Existing user GitNexus assets are removed only through the confirmed cleanup path (see [Cleanup runtime](#cleanup-runtime)); the npm package, the GitNexus CLI and `~/.gitnexus` global data always remain untouched. Explicit Codex/OMP graph/MCP wiring is described below.

RTK remains optional and retains its confirmation flow. Onboard verifies the binary with an isolated `gain` probe, because running it in an empty user HOME creates a history database. `verificationScope=isolated-probe` means actual user-history directory permissions and contents were not verified. Do not interpret probe success as a repair of the user's data directory.

## npm and nvm

Installing a missing selected Agent or an explicitly accepted npm-backed tool requires npm. A working local Graft/Agent is not blocked just because npm/latest lookup is absent. On macOS and Linux, prerequisite installation remains explicit:

Plain `check` is an inventory, not a selected npm install. Missing npm/Node/nvm are listed under `installationReport.conditionalRuntime` with `status=conditional`, not under its failure buckets or `missing.runtime`. Actual install handlers still validate their required runtimes and reject missing prerequisites before writes.

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

The retired `trellis-workflow` and `trellis-channel` bundled Skills were removed from the catalog and the template tree in the same atomic change that added `sbtd-task` (source `templates/skills/sbtd-task`); no alias or compatibility copy is installed. User-global copies of the retired directories are deliberately left untouched by this change — their retirement cleanup is owned by the confirmed legacy cleanup path (see [Cleanup runtime](#cleanup-runtime)).

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
- `sbtd`: the selected-state inspection with `status`, `reason`, `nextStep`, `validationScope`, `activeTask`, `bootstrapTask` and `legacyPresent`; a present bootstrap record appears under `sbtd.bootstrapTask.relativePath`

Removed `trellis.*` setup fields have no aliases.

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

Unconfirmed `promote` / `archive` calls return read-only transfer previews. Other mutating calls, including `rebind` and `protect_local_state`, raise `TaskStateError` when confirmation is missing; they do not write. `promote` / `archive` return `TaskTransfer(status, task, source_path, target_path, files, retained_original, completed_steps)`. `protect_local_state` returns a boolean indicating whether protection was added. Failures report `reason`, `next_step` and actual `completed_steps`. Engineering boundaries:

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
- A writable `new` request without a task ID returns `needs-task-choice` before asking to persist. Accepted recommendations retain their reason and risk identity in `mode_note`; ordinary free-text notes remain valid. Repeating an already persisted `(mode, user source, note)` choice returns `ready` without reconfirming or rewriting.

`HandoffStore(tasks)` persists continuation snapshots under the protected `docs/handoffs/` only:

- `HandoffPolicy(task_opt_out=False, session_opt_out=False)` carries two independently latched opt-outs; session opt-out is reported first and manual save bypasses neither read-only nor confirmation/redaction checks. `save(task_id, content=..., trigger=..., policy=..., confirmed=False, redaction_confirmed=False)` returns `HandoffResult(status, persisted, path=None, snapshot=None, reason=None)`. Statuses remain `suppressed`, `conversation-only`, `branch-conflict`, `unprotected`, `unchanged`, `pending-confirmation`, `needs-redaction` and `saved`; their full conditions are in `templates/skills/sbtd-task/references/handoff.md`. Deduplication compares only the latest snapshot for the task, excluding `created_at`; older matching history does not suppress a new context.
- `protect(confirmed=False)` returns True when it appends the root-anchored `/docs/handoffs/` rule and False when already protected; missing confirmation, read-only scope, tracked state, or hiding unknown existing data raises `TaskStateError`. Non-Git rules retain literal leading spaces and use the last exact relevant positive/negative rule; uncertain patterns do not prove protection. The helper never initializes Git or overwrites foreign files.
- New file names are `docs/handoffs/{YYYY_mm_dd}-<sha256>.md`, with a fixed-length lowercase SHA-256 digest of the UTF-8 full task ID. Existing reversible full-ID hex names stay readable without renaming. Filename ownership is checked against the full `task_id`; the filename alone is never authority. Snapshot fields remain `schema_version`, `task_id`, `task_path`, `task_status`, `workflow_mode`, `mode_source`, `mode_note`, `project_root`, `branch`, `head` (null for unborn HEAD / non-Git), `created_at`, `content`, `policy`, and `redaction`. Content requires `goal` / `next_action` / `limitations` strings and `decisions` / `completed` / `remaining` / `changed_files` / `verification` / `do_not_repeat` string lists, plus optional JSON-compatible `presentation`; unknown keys are rejected.
- `load(relative_path)` requires the closed schema version 1, a filename key matching the task ID's SHA-256 or legacy reversible hex, and the current `project_root`. Malformed, unowned or foreign files raise `TaskStateError`. Snapshots of any age can be explicitly loaded without changing the task. `reminders(now=None)` returns snapshots at most seven days old, latest per task, for matching root/branch and unfinished tasks; malformed or foreign files are skipped and each returned dict adds its `path`. No automatic session-start capability is claimed.

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
- Text-mode writes print the final developer result as well as preflight. Identity outcomes `conflict`, `blocked`, and `needs-*` exit 2; actual `failed` outcomes exit 5. Completed writes remain reported for either category.
- Without `--developer` nothing changes: no command creates, repairs or requires an identity, and `reset` preserves any existing file.

Ordinary resolve/plan/check/global installation never reads `.trellis/.developer`; authorized legacy identity migration remains the separately gated P1-12 task and is not claimed complete by this helper. The root installers forward the implemented public flags without adding a developer-specific option. Windows proof, full validation and release remain unclaimed.

## Migration Runtime

The installed Onboard script exposes `migration --phase plan`, `apply`, `verify` and `cleanup`, plus the separate `recovery --phase plan|apply` mode and the fresh-detection `cleanup-legacy --phase plan|apply` mode. This is not a second CLI, and there is no positional `migration plan` alias. Batch cleanup consumes the bound verification record and an explicitly confirmed `verification_id`; recovery consumes the manifest-scoped evidence chain and an explicitly confirmed `plan_id`; `cleanup-legacy` consumes a freshly sealed cleanup plan and an explicitly confirmed `plan_id`. Do not use this unreleased stage to perform a real-project cutover before the remaining integration validation, Windows-native proof and release gates are available and accepted.

### Authorized preparation and plan

- Resolve the actual selected project roots, whole shared HOME/host batch, custodian and private storage explicitly. Never infer authorization from a valid checksum or a sample label.
- Prepare an existing owner-private vault outside every selected project. Publication decisions and approved candidates must already exist inside that vault; plan never creates them. POSIX owner/mode and Windows ACL checks are separate; unproven privacy, links, aliases or unknown types block.
- `routing-approvals` is a separate private record for an already approved AGENTS.md candidate. The record must include an Ed25519 signature over its canonical `schema_version` and `items`. Apply and plan verify that signature with `assets/routing-approval.pub` from the installed package, resolved from the installed script path. The public key is not read from the manifest or from a caller path. Plan may sign an existing approval file only when given `--routing-approval-key`; that key must stay outside the vault and selected projects, its path is not sealed, and a key that does not match the installed public key is rejected before the signature is written. Apply does not read a private key. The caller must still pass `--routing-approvals`; its SHA must match the sealed record, and the operation set is rebuilt from that file. A caller who points that path at an attacker file fails signature verification before write. Without that file, apply requires explicit `--no-routing-approvals` and refuses pause-block append or management-block deletion on `AGENTS.md`. Omitting both is not "no approval".
- The characterized legacy input is Trellis v0.6.17. Generated runtime files remain in the private-preserved legacy tree until later cleanup. Unknown ownership or customized/mixed shared configuration blocks for reconciliation; a mutable legacy hash alone cannot authorize deleting foreign entries. Old configuration pins are compatibility facts, not a latest-version update target.
- Gitignored paths under `.trellis` that sit outside the known layout are incidental. Plan does not require approval for them, but the directory snapshot still contains them, so later cleanup removes them together with the rest of `.trellis` through the vendor uninstall. `tasks`, `spec` and `lessons` stay in the approval closure even when gitignore matches them. A path outside that layout that git does not ignore stops the plan and is listed for an explicit decision; plan does not delete it.

#### Canonical legacy task candidates

The unreleased v2 candidate validator binds mapped state to the preserved `task.json`, rather than accepting prose as machine evidence. Unknown old fields stay in `legacy-task.json` (or the private original); they must not become current frontmatter extensions. Independently validated current fields are regenerated, not copied from coincidentally named old fields.

- Unproven mode is `workflow_mode: null`, `mode_source: migration-unknown`, and `mode_note: legacy Trellis task without mode proof`.
- A proven completed legacy task has one `unknown -> done` event. Its reason is exactly `legacy completion fact`, evidence exactly `legacy task.json status`, and time is the provable completion timestamp or `unknown`. Extra narrative belongs outside that authoritative event.
- The task body has exactly one top-level `sbtd-legacy-time-provenance` fenced JSON block. Include exactly the timestamp fields whose current frontmatter value is null, using the following fixed source/status values; omit a field when its timestamp is provable. These labels refer to preserved source facts, not public JSON pointers: they remain truthful when the shared sidecar is redacted or root-private.

```sbtd-legacy-time-provenance
{
  "created_at": {"source": "legacy task.json: createdAt (sidecar or private original)", "status": "unproven"},
  "updated_at": {"source": "legacy task.json: no recorded update time", "status": "unproven"},
  "completed_at": {"source": "legacy task.json: completedAt (sidecar or private original)", "status": "unproven"}
}
```

Candidates prepared under the earlier permissive grammar must be regenerated in the private preparation area and reapproved; do not rewrite an already sealed manifest or its approved bytes. Historical archive positions map to the proven quarter or `undated`; an ordinary completed task is not automatically archived. Local Markdown links/images must resolve to approved publication targets; escaping paths, local file URLs and unsafe schemes are rejected.

**Link-policy boundary:** reject any Windows drive prefix (`C:secret.md`, `C:/secret.md`, or `C:\secret.md`, including percent-encoded spellings) before treating a URI scheme as external. Ordinary project-relative links still need an approved target. Other protocols keep the existing markdown-it safety policy: this is not HTTPS-only and does not ban every data URI; HTTP, mailto and parser-approved image data URIs remain supported, while unsafe destinations remain rejected. Validation never fetches the link.

**Exit-policy boundary:** a rejected link remains a pre-publication `target-conflict` (the CLI reports blocked/2). This repair does not change execution-phase status aggregation, preservation failures or partial-receipt semantics. Any broader 2/3/5 reclassification must separately define preflight refusals versus failures after writes and update the matching status/retry contracts; it is not bundled with this path fix.

**Private continuation handoffs (PLAN-008):** the fixed legacy format is `.trellis/.runtime/sessions/*.json` with `current_task`; nonempty old `.current-task` path lines and unknown session shapes require reconciliation. Workspace journals remain complete private originals. If journals exist, every unfinished migrated task needs its own explicitly approved handoff; session-only context requires the referenced unfinished tasks. Multiple tasks are preserved separately, never auto-selected.

Prepare each reviewed, redacted summary in the private vault using the existing `HandoffStore` Markdown snapshot format. Its publication item uses `decision: redact`, `required: true`, binds every original journal/session file in `sources`, and targets `docs/handoffs/{YYYY_mm_dd}-<sha256-of-task-id>.md`. Match the migrated task's identity/path/state/mode/branch and the planned HEAD; supply a nonblank goal, remaining work and next action. Approval covers the exact candidate bytes and source snapshots. The planner generates neither summaries nor approvals. Raw journals, private hashes and session metadata remain in the private backup rather than shared task records.

Plan is read-only. Apply uses existing ignore protection and copy operations; retry, verify, cleanup and recovery retain their bound-original and candidate checks. Missing approval, stale/foreign task references, unknown runtime content without a private-only decision, changed candidates or tracked handoff storage block. An explicit private-only item can skip one whole legacy task folder or preserve spec files without publication or a handoff; lessons still need a share/redact projection, and a missing or partial skip still blocks. A session pointer to that complete skip is allowed. Unknown, external, or partial-skip pointers still block. A handoff can be loaded through `HandoffStore` after apply, but does not set active-task or choose a mode for an unproven legacy task.

Command shapes below require actual authorized values in place of angle-bracket arguments:

```text
python <installed-onboard.py> migration --phase plan --projects-root <comma-separated-absolute-roots> --backup-root <external-private-vault> --custodian <actual-label> [--publication-decisions <private-file>] [--routing-approvals <private-file>] [--routing-approval-key <private-key-outside-vault>] [--successor-manifest <private-manifest-file> --successor-apply-receipt <complete-private-receipt> --deployment-mode init|init-projects] --json
python <installed-onboard.py> migration --phase apply --manifest <private-manifest-file> [--apply-receipt <prior-private-receipt>] (--routing-approvals <private-file> | --no-routing-approvals) --yes --json
python <installed-onboard.py> migration --phase verify --manifest <private-manifest-file> --apply-receipt <complete-private-receipt> --deployment-evidence <private-deployment-file> --json
python <installed-onboard.py> migration --phase cleanup --manifest <private-manifest-file> --apply-receipt <complete-private-receipt> --deployment-evidence <private-deployment-file> --verification <private-verification-file> [--cleanup-receipt <prior-private-cleanup-receipt>] --confirm-cleanup <current-verification-id> --json
python <installed-onboard.py> recovery --phase plan --manifest <private-manifest-file> [--apply-receipt <partial-apply-receipt>] [--deployment-evidence <partial-deployment-evidence>] [--cleanup-receipt <partial-cleanup-receipt>] [--projects-root <comma-separated-absolute-roots>] --json
python <installed-onboard.py> recovery --phase apply --plan <private-recovery-plan-file> [--recovery-receipt <prior-private-recovery-receipt>] --confirm-recovery <current-plan-id> --json
python <installed-onboard.py> cleanup-legacy --phase plan --projects-root <comma-separated-absolute-roots> --backup-root <existing-private-directory> [--global-skills-dir <skills-root>] --json
python <installed-onboard.py> cleanup-legacy --phase apply --plan <private-cleanup-plan-file> [--cleanup-receipt <prior-private-cleanup-receipt>] --confirm-cleanup <current-plan-id> --json
```

Each command returns one envelope. Subsequent file arguments require the corresponding bare subobject: `response.migration.manifest`, `response.migration.apply_receipt`, `response.migration.verification`, `response.migration.cleanup_receipt`, `response.recovery.plan`, `response.recovery.receipt`, or `response.cleanup_legacy.plan` / `response.cleanup_legacy.receipt`; the whole response envelope is not a manifest/receipt/plan. Store output only in the authorized private location. Explicit caller-side saving does not make plan/verify writable.

A successor deployment batch repairs a completed batch whose sealed plan carries no deployment declaration: pass `--successor-manifest` and `--successor-apply-receipt` as a pair (no directory discovery; each stays in its own private directory — the manifest directory and the backup vault are separate private areas) together with an explicit `--deployment-mode`. The predecessor must have `deployment: null`, no successor binding of its own, and a fully successful apply receipt. The planner re-verifies the bound documents, the exact root set, vault and custodian, and re-measures every completed apply outcome and every carried cleanup target; any drift blocks instead of relaxing the pre-state. The sealed successor manifest carries only the pending legacy/skill retirements plus the deployment closure, inherits the predecessor retention verbatim, embeds the predecessor's succeeded apply results under `payload.successor` alongside `manifest_ref`/`apply_receipt_ref` content-hash references to the real predecessor files — those two files must not be moved or rewritten for the lifetime of the successor chain — and lets deployment `before_requirement` reference them across manifests. Every consumer (apply/deploy/verify/cleanup) re-loads the referenced predecessor documents and rejects altered embedded results, a reduced carried cleanup set, or drifted completed outcomes. Apply, verify, cleanup and recovery consume the chain through the ordinary bound documents with no new flags. Successor inputs are mutually exclusive with `--publication-decisions` and the routing-approval options.

### OMP follow-up deployment

Use a followup batch only after a Codex predecessor has completed apply, deployment, verified verification and cleanup. This is a separate path from a successor batch; successor-of-successor stays rejected. The predecessor may be an original or successor batch, not another followup. All five files must be supplied together; do not discover them by scanning directories:

```text
python <installed-onboard.py> migration --phase plan --projects-root <same-absolute-roots> --backup-root <same-private-vault> --custodian <same-label> --followup-manifest <predecessor-manifest> --followup-apply-receipt <predecessor-apply> --followup-deployment-evidence <predecessor-deployment> --followup-verification <predecessor-verified-record> --followup-cleanup-receipt <predecessor-cleanup> --deployment-mode init --deployment-platform omp --json
```

Followup inputs are plan-only, mutually exclusive with successor/publication/routing approval inputs, and reject hooks. The manifest seals five immutable file references and their IDs under `payload.followup`; preserve those files in their private locations for the entire followup lifetime. Every consumer rechecks their bindings, success states, retained backups and non-overwritten outcomes. Project roots, platforms, vault, custodian and retention are inherited; Git revision is observed again. Missing ignore protection blocks instead of adding a data-migration operation.

Review the complete plan before authorizing deployment: it includes project AGENTS/graphs, canonical global rules/Skills and OMP MCP, not just one MCP file. An older managed installation can be replaced only when its target and current state are proven by the predecessor's successful results. Unknown customizations remain conflicts. The new batch uses concrete before-states, empty project sources and no apply/legacy-cleanup operations; it does not relax old successor rules or the current batch's runtime/source checks. Historical predecessor source files need not equal the new release's templates.

Predecessor-owned overwrite targets bind differently by ownership: configure-graft section targets (Codex config.toml, hooks.json, OMP mcp.json, project AGENTS.md fences) prove their managed section and seal the current live snapshot, so fence-exterior host or user text carries over; directories and other whole-resource targets still pin the recorded historical after-state, and resealing a followup cannot adopt later user changes. For section targets the interpreter, node and cli paths are checked by argv shape and cross-entry consistency only — a same-shape path swap still passes. Codex launchers must sit inside a live directory deployment target from the same gate run — retired cleanup targets never anchor — and managed hook commands must match the canonical render for their event; OMP launchers stay shape plus cross-entry consistency because that chain has no verified directory containing them. Directory upgrades pass their verified retained backup to the existing replacement primitive so recovery can restore the older installation. Deployment evidence output cannot overlap predecessor/ancestor documents, source or stage backups, publication candidates, report artifacts or other sealed inputs; a new file inside a protected directory is also an overlap. A disjoint sibling evidence directory within the private vault remains allowed.

After saving the bare manifest privately, use the ordinary confirmed apply with `--no-routing-approvals`, then the existing `init` migration deployment context and ordinary verify inputs for this new batch. No new flags are needed by later phases: the manifest carries predecessor references. Empty cleanup does not authorize deletion. Recovery restores only this followup's proven writes to its own before-state; it does not undo predecessor cleanup, reactivate Trellis or remove any predecessor/followup backups. Actual HOME deployment, OMP session restart and `initialize` / `tools/list` / root-bound query proof remain separately authorized operational work.

### Apply, retry and verification

Apply first checks the complete batch and current runtime/input bindings, retains full original bytes and empty directories, then installs only approved projections and required local protection. Legacy identity is explicitly extracted into a genuinely missing current identity; ordinary identity lookup is unchanged. Proven owned Codex and existing OMP global routers receive the maintenance pause, with one shared result and full declared dependent-project closure. An absent OMP root is not created. The existence check classifies only that root and does not walk its children. Every path component, including parents, is checked without following links. A link, file, or special entry on that path is rejected. Unrelated links inside the directory are not an existence failure and are not modified.

Successful or handled partial applies atomically save a new `apply-<apply_id>.json` beside the manifest before returning its copy. Retry must explicitly supply that receipt; completed unchanged resources and their original backups are preserved, only legal unfinished work resumes, and unattempted shared operations cannot be reported as observed. There is no implicit receipt discovery, cross-resource transaction, guessed rollback, or deletion of old data. If receipt persistence or preservation fails, stop and retain all private artifacts; do not retry from guessed state.

Verify requires complete successful apply plus bound deployment evidence and actual native report files; it never invokes deployment or smoke. It rechecks source/revision/runtime, originals/backups, approved publications, report digests and scope, actual retained resources and future cleanup candidates. A route whose latest bound successful operation proves `after=absent` is not a retained present asset; missing publications or an unproven disappearance still fail.

Native report schemas remain unchanged. Outer migration `source_ref` stays null for a detached or non-Git project. Native report `sourceRef` is the explicit label `HEAD` for detached Git with the exact OID, or `non-git` with null commit and unknown source revision outside Git; these labels are not invented branch names. Ordinary named refs remain exact. First-deployment report times must lie inside that deployment attempt. A cumulative retry may retain successful report bytes only within the same bound apply epoch, from the supplied apply receipt's `finished_at` through the latest deployment finish. Reports still require exact root/ref/OID, verified environment, non-mock smoke mode, command, captured stdout/stderr and clean exit; an optional `processExitCode`, when present, must also be integer zero.

Declared non-API auxiliary reports require native evidence v2 and a supported `junit-xml-v1` or `playwright-json-v1` report, with a uniquely matched passing case carrying the source-locator digest. Every linked locator must match the enclosing repository key, source ref and commit. Unsupported/untyped auxiliary reports fail closed. Auxiliary report mode does not trigger the API genuine-mode gate, and an auxiliary report never replaces the required genuine API smoke. A state-consistent batch report may be referenced by multiple projects; conflicting states or strict ancestor/descendant report paths remain invalid.

`tool_versions` binds installed migration source/assets, declared dependency versions and Python, plus the selected Graft target pin; it is not proof that Graft or a host was executed. A consumer may accept one predecessor runtime only when its signed pairing verifies with `assets/runtime-lineage.pub`, the current `onboard` hash equals that successor, and the caller supplies the manifest's complete successful apply receipt. After callers validate the full evidence bindings, known deploy and cleanup outcomes supersede apply outcomes in that order; a bound recovery receipt then supplies the latest succeeded inverse state. Current targets must match that latest proven state and retained backups must still match. Unknown forward states are rejected, not replaced by an older apply state. A failed stage can have a known changed outcome: recognizing it does not permit ordinary partial-write retry; explicit recovery still requires its valid before backup and confirmed plan. An ordinary apply retry receives no later-stage evidence and still requires its own apply outcome.

The pairing file stays outside the runtime fingerprint; the public key and verification code stay inside it. An unlisted successor, bad signature, incomplete apply receipt or evidence mismatch remains fail-closed. This exception neither waives fresh-plan checks nor authorizes a new write. Consumer fixtures prove their stated boundaries, not real host deployment; Windows ACL execution and host deployment require their own environment proof. No valid hash or task status waives a missing required check.

### Cleanup runtime

Cleanup has two entry points over one detection and execution engine. The batch entry `migration --phase cleanup` consumes the bound verified verification record and an explicitly confirmed `verification_id`; its sealed candidate set, cumulative receipt and retry semantics are unchanged, and immutable batch manifests never gain the new target kinds — project `.gitnexus/`, gitnexus MCP entries and AGENTS marker blocks are always handled by a fresh plan, never by hidden batch scope expansion. The fresh entry `cleanup-legacy --phase plan|apply` re-detects every supported target live and binds the confirmation to a freshly sealed plan. Neither id is authentication or ownership proof; each only binds one explicit confirmation to the candidate set that was displayed and sealed.

After a verification whose `status` is `verified`, the Agent proactively offers cleanup: it displays the batch-sealed candidates from the verification's per-project `cleanup_candidates` and `shared_cleanup_candidates`, and runs `cleanup-legacy --phase plan` so the actual fresh candidate list is displayed as well — the combined confirmation happens only after both lists are shown, and items that were not detected are not listed. A user who declines is told that `sbtd cleanup`, `清理工作流` or the same explicit intent re-triggers the flow later. The trigger authorizes read-only detection and planning only; the explicit yes after the displayed scope authorizes execution, and one confirmation covers the displayed combined scope of batch-sealed and freshly planned candidates. Run the batch cleanup first; if it changed originals sealed by the fresh plan, regenerate that plan and display the remaining work. During the same confirmed cleanup run, the original consent also covers a plan that only removes overlap targets proven completed by the bound batch receipt, provided the remaining targets and effects are unchanged. This ordinary reduction needs no second yes; added targets or changed effects require renewed consent. Unexplained disappearance, user edits and conflicting/failed evidence still stop the flow for reconciliation. Use the current plan's id even when consent carries forward. The Agent reads `verification_id` / `plan_id` from the CLI JSON output itself; the user never pastes a hash. Normal `init` / `reset` never performs this cleanup. Entry selection is batch evidence first: only missing batch evidence falls back to a fresh plan for the retired `.trellis` / Skill targets as well, while stale, conflicting or failed batch evidence is preserved and resolved first — never used as a fallback reason to bypass a gate.

Detected candidate kinds:

- `trellis-uninstall` — a project `.trellis` directory. Removal actually runs the vendor `tl uninstall` with the project root as the working directory, driven by a dedicated adapter: plan-time preparation computes the complete vendor footprint, and before execution the footprint — `.trellis` plus the platform configuration and AGENTS entries the vendor uninstall may modify — is privately backed up. A missing CLI or a failed preparation blocks the target without executing; there is no engine direct-delete fallback and no `rm -rf`. An incomplete uninstall fails the resource and the receipt records per-resource measured after-states, so partial mutations are reported as measured evidence and must be reconciled before any retry — never claimed untouched. Batch cleanup removes its sealed `.trellis` targets through the same adapter and full-footprint backup with the existing before/after checks unchanged. A symlinked `.trellis` is blocked, not a candidate.
  Each prepared resource path must exactly match the checked project root joined with its strictly validated relative path, and execution compares the bound paths with the fresh planner replay. Resealing the descriptor does not authorize a decoy path: a mismatch is rejected as `invalid-document` before adapter backups or vendor execution. Backup, state rechecks and outcome measurement consume only bound paths. The persisted scope fingerprint shape and digest algorithm remain unchanged for valid existing plans.
- `skill-directory` — a global `trellis-workflow` or `trellis-channel` directory under the resolved global Skills root, proven by identity: a non-symlink directory whose regular `SKILL.md` frontmatter `name` exactly matches. Content drift across 1.0.x versions does not matter; there is no fixed checksum pin. A symlink, a missing or unreadable `SKILL.md`, or a mismatched `name` is blocked and preserved.
  A physical shared HOME root does not authorize every same-named directory beneath it. A standalone `shared_root` of kind `skills` binds its own `path`; when that root is absorbed into a broader record, the manifest retains its exact logical directory as `shared_root.skills_root`. Producers preserve this annotation through root merging, and consumers require the retired Skill to be its direct child. Missing logical scope for an absorbed retirement fails closed; it is not reconstructed from the current environment or from the target's basename.
  Fresh `cleanup-legacy` additionally recognizes the nine exact GitNexus Skill identities listed in [Upgrade Alignment](#upgrade-alignment). This does not widen immutable migration manifests or authorize prefix-based removal; the same direct-child, identity, backup and separate-confirmation checks apply.
- `directory-remove` — a project `.gitnexus/` directory; a symlink is blocked. This is project-local data only: the GitNexus npm package, its CLI and `~/.gitnexus` global data are never cleanup targets, and no CLI/npm uninstall is performed.
- `mcp-server-remove` — gitnexus server entries in an already existing host global configuration file. Only existing files are probed and nothing is created; the user home resolves from `HOME` or `USERPROFILE`:

  | host | probed existing paths | format |
  |---|---|---|
  | codex | `$CODEX_HOME/config.toml` and `~/.codex/config.toml` | TOML |
  | claude | `~/.claude.json`; `~/.claude/mcp.json`; `$CLAUDE_CONFIG_DIR/mcp.json` when set | JSON |
  | kimi | `~/.kimi-code/mcp.json`; `~/.kimi-code/config.toml`; `~/.kimi/mcp.json` | JSON / TOML |
  | omp | `~/.omp/agent/mcp.json`; `$PI_CODING_AGENT_DIR/mcp.json` when set; each existing `~/.omp/profiles/<profile>/agent/mcp.json`; the effective configuration resolved by the existing `active_omp_paths` resolver — relative `$PI_CONFIG_DIR` override with `OMP_PROFILE` taking precedence over `PI_PROFILE` | JSON |

  An entry identifies as gitnexus when its key is `gitnexus` / `gitnexus-mcp`, its command is a gitnexus binary, or its npx/node arguments name the gitnexus package. Removal deletes every detected gitnexus entry from `mcpServers` (JSON) or `[mcp_servers]` (TOML) and nothing else. JSON files are parsed strictly (duplicate keys rejected) and rewritten under the existing MCP write convention (normalized layout, UTF-8, trailing newline); TOML files go through a format-preserving tomlkit round-trip. Neighboring servers and all other content are preserved. An unparseable, symlinked or non-regular configuration is blocked and preserved. Spelling aliases of the same directory entry are probed once; distinct hardlink entries remain separate targets because atomic replacement changes only one entry. These files are shared by every project on the host: the displayed scope discloses that impact and the confirmation covers it.
- `marker-blocks` — a project `AGENTS.md` containing exactly one ordered pair of `<!-- TRELLIS:START -->` / `<!-- TRELLIS:END -->` (uppercase) and/or one ordered pair of `<!-- gitnexus:start -->` / `<!-- gitnexus:end -->` (lowercase), each recognized only as a top-level HTML comment block — a marker-looking line inside a code fence or inline context is ordinary content, not a marker. Removal deletes the paired blocks with their contents; every byte outside the spans, including `<!-- graft:start -->` / `<!-- graft:end -->` fences and project-owned content, is preserved. Zero pairs is not a candidate; duplicated, interleaved, nested or unmatched markers are blocked and listed for manual resolution — the file is never guess-edited.

Fresh path contract:

```text
python <installed-onboard.py> cleanup-legacy --phase plan --projects-root <comma-separated-absolute-roots> --backup-root <existing-private-directory> [--global-skills-dir <skills-root>] --json
python <installed-onboard.py> cleanup-legacy --phase apply --plan <private-cleanup-plan-file> [--cleanup-receipt <prior-private-cleanup-receipt>] --confirm-cleanup <current-plan-id> --json
```

`plan` does not mutate cleanup targets: it detects every candidate kind above for the selected roots, the resolved global Skills root and the existing host MCP files, snapshots each before-state, seals the private backup root / home / Skills root and the prepared vendor-uninstall descriptor for each `.trellis` candidate, and saves `cleanup-legacy-plan-<plan_id>.json` inside the verified private backup root; the JSON envelope carries `cleanup_legacy.plan` and its private `plan_path`. The plan-time global Skills root follows the existing resolver precedence — explicit `--global-skills-dir`, then `$AGENT_SKILLS_DIR`, then the trusted installed Onboard parent directory, then the platform default — and is sealed into the plan; `apply` consumes only that sealed root, accepts no Skills-root option of its own, and is not redirected by a changed environment. This override exists only on `cleanup-legacy --phase plan`: migration phase arguments and `cleanup-legacy --phase apply` are unchanged. Both phases reject, before any target write, candidate paths that are equal to or nested inside one another — for example a selected project `.gitnexus` containing a selected retired Skill directory — leaving every original untouched rather than relying on execution order. A target whose vendor preparation fails is recorded as blocked, and any blocked item makes the plan result `blocked` (exit 2); with no candidates the result is `nothing-to-clean` (exit 0). `apply` requires `--confirm-cleanup` equal to the current sealed `plan_id` and the plan file still in its declared private backup root; a plan whose content no longer matches its `plan_id` is a binding violation and stays blocked. Apply refuses while any blocked item remains and re-validates the whole scope before writing: the home and selected Skill root must match the plan and every remaining candidate must retain its authorized identity and intended effect. A first execution requires the sealed before-state; a receipt retry may instead use an exactly matching after-state from a proven successful vendor transition bound to that plan's prepared resources. Original backups are immutable and reused for those transitioned candidates; remaining marker edits are rendered from the original bytes, not from the partly scrubbed file. Unexpected drift or unproven state still blocks. When a successful batch has changed fresh-plan originals, regenerate the fresh plan and use its new plan_id; this token refresh does not itself require a second user yes. Within the same confirmed flow, unchanged targets/effects or a receipt-proven completed-only reduction retain the original consent; added targets or changed effects require renewed consent, and unexplained changes require reconciliation. Every candidate original is privately backed up before execution begins, then each resource executes fail-stop and its after-state is verified against the intended goal: absent for removals, exact rendered bytes for file edits. A cumulative `cleanup-legacy-receipt-<receipt_id>.json` is saved atomically beside the plan; if saving fails after writes, the run reports failure and the private backup directory must be preserved. An explicit retry passes the prior `--cleanup-receipt` of the same plan; proven successes are not replayed. Failed/partial vendor work, forged transition evidence, user edits, or an unsuccessful resource's unexplained after-state block retry until reconciled. Exit codes: plan 0 planned / nothing-to-clean, 2 blocked; apply 0 cleaned, 2 blocked, 3 failed. Non-JSON output prints only the status; detailed references stay private.

The `recovery` CLI consumes migration-batch evidence only; it does not accept cleanup-legacy plans or receipts. Fresh-path backups are retained private files with no automated restore command; restoration from them is a manual custodian operation under the retention and destruction rules below.

### Backup retention and manual destruction

Backups are retained independently of migration cleanup, Graft uninstall, task completion and recovery success. No phase in this Onboard runtime deletes original backups, approved candidates, manifests, stage receipts or registered copies, and no new disposal CLI, lifecycle file, journal, lock, scheduler or evidence index is added. A manifest records the non-sensitive custodian, the explicit external private `backup_root`, the managed backup inventory and the minimum retention requirement; the normal release path keeps backups through the P3 two-week observation and at least 14 days after formal release, whichever ends later, unless the project explicitly extends it or a stricter privacy/legal requirement forces a different preservation plan before migration proceeds.

Recovery is available only while the bound manifest, stage/recovery receipts, actual backups and registered copies still prove ownership, exact scope and current state. A legal partial apply/deploy/cleanup may be recovered only for the proven writes; missing, incomplete or conflicting evidence, unknown files, symlink escape, changed targets or resources in use are evidence-insufficient and stay blocked with zero deletion and no done claim. Recovery success restores only the bound managed data and configuration comparison state; it never invokes, reinstalls, or resumes the retired Trellis runtime, and restored files never imply that runtime is executable or writable — its `runtime_readiness` stays not-verified and must not be inferred from recovery success. Recovery success never authorizes backup destruction and does not end the maintenance window: maintenance does not end automatically before the bound deployment acceptance. A same-runtime partial receipt retry only resumes that batch's unfinished writes; it is distinct from the predecessor-acceptance path above, which separately requires the signed predecessor-successor pairing and the manifest's complete successful apply receipt. Live receipts prove only the actual live state they observed; fault injection, partial retry, and recovery resume must each be proven by fresh isolated tests, and neither kind of evidence substitutes for the other.

Manual destruction is a custodian operation outside cleanup. Both the normal-release branch and the explicit migration-abandonment / release-cancellation branch require unresolved migration/recovery issues to be closed, no operation using the backups, no audit retention requirement, and a separate destruction authorization. The normal branch also requires the completed release readiness decision and the retention window to have ended; the termination branch requires the recorded termination decision, accepted necessary recovery and an explicit custodian close-out of remaining rollback needs. If P2-01 has not completed and no manifest exists, the termination branch may only process preparation artifacts whose ownership is proven by private publication-decision candidates and preparation authorization or an existing migration report.

Before any deletion, the custodian or an explicitly authorized Agent must save and reread, in an existing private preparation record or migration report outside the deletion scope, the non-sensitive custodian label, candidate ownership, exact destruction scope, this independent authorization and the actual confirmation time. The record location must first be verified private, writable and able to retain the note in its existing format; closed publication-decision schemas are not extended arbitrarily. Any missing item, including confirmation time, or any save/reread failure is blocked, deletes nothing and is not done. Destruction then rechecks each unchanged listed object in the same controlled window, deletes only listed objects, records actual deleted/failed/remaining results in the same record, and leaves unresolved paths privately retained for review. Interruption or failure preserves real results; retry rechecks the remaining list and obtains confirmation again, never treating a later same-name file as the old backup.

## Codex and OMP Wiring and Deployment

Explicit `--platform codex|omp` selects Graft host wiring in Python `init`/`reset`, even with no project roots. `--projects-root <absolute-roots>` additionally selects local graph preparation; `init-projects` remains project-only. Setup never installs or upgrades Graft/Node implicitly. Missing pinned runtime reports `graftWiring.status=not-available` for optional normal setup; explicitly authorized hooks, legacy cutover and sealed migration remain blocked. Ownership/configuration/scope failures are never downgraded. Project templates precede the fence; `--skip-project-agents` preserves surrounding instructions. Global-only success means the definition was installed, not that a project graph was queried.

`graftWiring` in `check` and `plan` is read-only installation feasibility for the selected scope, not a health certificate for the currently installed project instructions. When project AGENTS replacement is selected, pre-render the canonical template that would be backed up/applied by the later confirmed install; `--skip-project-agents` instead validates the current file. `status=planned` never authorizes a write or claims the current bytes were repaired. Root installers use the same preflight before installation.

OMP plugin MCP manifests are not modeled by this installer. The preflight conservatively rejects any discovered installed-plugin registry, including Claude configuration overrides, OMP base/profile/XDG data roots and the nearest selected-project registry. This guard does not depend only on an explicit `claude-plugins` user opt-in: the pinned host can load OMP-origin and project plugin roots by default. No registry is rewritten or plugin executed.

Full setup merges one stable global `sbtd-graft` server into the effective host configuration domain, with absolute installed runtime/launcher arguments and neither a fixed `cwd` nor a project `--root`. Repeating setup or adding another project does not add another server. Foreign configuration is preserved and conflicting managed definitions block. Project-only setup writes no HOME, global Skill or MCP/hook configuration. Existing AGENTS mirror policy remains separate from OMP MCP wiring; sealed migration lists its shared writes before confirmation.

For `--platform omp`, full `init` writes only the active OMP user MCP target: default `~/.omp/agent/mcp.json`, named-profile `~/.omp/profiles/<profile>/agent/mcp.json`, or default-profile `PI_CODING_AGENT_DIR`. It never writes hooks. Plan/execute snapshots every static OMP, Codex and Claude source it reads; inherited equivalence follows OMP's complete connection identity, not just command shape. Existing enabled equivalent connections leave an absent OMP target absent, while disabled managed entries, conflicting definitions, server/extension denylists, dynamic overlays, agent `.env`, legacy settings and provider-setting project files block rather than infer an effective host state. Migration plan selects this producer with `--deployment-platform omp`; `init-projects` declares only project fence/graph resources and has no shared MCP operation.

Batch setup rejects nested or mutually containing selected roots before any runtime probe. Each selected root receives its own graph; batch and incremental setup use the same project operation. At MCP startup the launcher finds the nearest real Git repository/worktree from the actual process cwd and locks it for the connection. Root proof uses an external Git executable from absolute PATH entries, excludes project-local/relative entries, scrubs inherited `GIT_*` and disables system/global Git config. HOME, no repository, malformed boundaries, uninitialized nested repositories, missing/old stamps and unsafe graphs fail closed without borrowing a demo, parent or sibling graph. Hook/analyze commands retain their explicit root; MCP rejects `--root`. Changing shell cwd does not retarget an existing connection.

On Windows the root proof selects `git.exe` by its fully qualified path in each external PATH directory and requires its resolved target to remain an `.exe` outside the project. It never searches cwd implicitly or executes `.cmd`/`.bat` wrappers through PATHEXT. Global OMP ownership checks require absolute launcher and CLI paths as well as their managed filenames; matching basenames alone do not certify a record.

The Windows Git root proof decodes output as UTF-8 independently of Python's default code page, so Unicode checkout paths do not depend on UTF-8 mode. POSIX retains its existing locale decoding. Undecodable proof output is a controlled `root-unsafe` refusal before downstream launch, never a reason to weaken root equality or borrow another graph.

Full installation binds MCP/hooks to the canonical installed Onboard Skill, not a disposable bootstrap checkout. That package is installed and verified before dependent host configuration is published. If ordinary init would retain a merely-valid but different older Skill shell, wiring preflight requests an explicitly confirmed reset instead of running the old guard. Project-only uses its existing executing package because it installs no global Skill.

Hooks are absent from the default write set. `--graft-hooks` is separate consent to install the managed definitions, not host trust or execution proof. The host must support and enable hooks and trust the exact configured hashes; Onboard never edits trust state or bypasses it. Preserve all foreign handlers. Host-event acceptance is a separate real-host check. The root installers forward this option through the implemented deployment flags.

The generated Python commands use `-E -s` before the installed script: caller `PYTHONHOME`/`PYTHONPATH` and user-site startup cannot run ahead of the guard, while trusted sibling modules remain importable. The launcher uses pinned native code, an ephemeral HOME, DNT and dotenv/LLM/cloud environment isolation. It validates current graph state before every MCP request; native automatic refresh stays disabled. A graph replaced by Stop or explicit deployment is rechecked before the running MCP receives another request. Invalid state returns a sanitized protocol error and stops that session rather than forwarding the request. Missing/old/incomplete stamps are never automatically reconciled. This is a single-controller adapter, not an OS sandbox or arbitrary concurrent-writer isolation.

An unrelated hook event is ignored before requiring the bound repository to exist; a deleted binding therefore does not break other projects. Relevant events still require valid runtime/root/graph state. Existing exact pre-hardening managed hook commands without startup isolation block authorized reconciliation instead of being preserved as foreign beside new commands; ownership conflicts require explicit resolution. Normal hook trust is never bypassed.

Normal wiring exposes `backupRoots` in the plan and retains existing resource originals in a private `<scope>/.sbtd/installation-originals/<run>/` directory. Existing installer template backups keep their original policy. Migration deployment instead uses the manifest's external private `backup_root`; its deployment evidence and native raw/Chinese-summary/envelope reports are new files within the manifest's private directory.

Codex MCP tables may be split across unrelated TOML sections, including a managed server's environment subtable. Candidate rendering preserves these valid table fragments, foreign values and comments without requiring a live-file normalization pass. This layout compatibility does not admit a top-level inline `mcp_servers` table or relax legacy runtime/root ownership and explicit-retirement checks. TOMLKit must be at least 0.13.2: [that release fixes incomplete deletion of split table fragments](https://github.com/python-poetry/tomlkit/blob/0.13.2/CHANGELOG.md). Retirement also reparses the serialized candidate and refuses any residual managed legacy entry; update the installed-copy dependencies rather than weakening this check.

Old `sbtd-graft-<root-hash>` entries are migration inputs, never newly generated. Normal setup refuses them. `--graft-retire-legacy` requires exact selected old roots and complete old command/argv/cwd/env/hash ownership. Across different runtime paths, additionally supply `--graft-legacy-bindings <private-json>` with `{"schema_version":1,"bindings":[{"root":"/selected/root","python":"/old/python","node":"/old/node","cli":"/old/dist/cli.js","launcher":"/old/scripts/sbtd_graft_entry.py"}]}`. The operator must inspect actual configuration/retained evidence before approving this contract. Its private parent, closed fields, selected roots, uniqueness, absolute paths and unchanged input snapshot are checked; it must stay outside deployment targets. Preview the plan before confirmed init; preserve its JSON result and original backups for scoped restore. Root wrappers forward these flags (`-GraftRetireLegacy` / `-GraftLegacyBindings` in PowerShell).

Project-only and sealed historical deployment contexts reject cutover options. Inherited old OMP sources cannot be deleted from another configuration domain. Historical receipts remain immutable and their old owned-section shapes are still verifiable; mixed old/new generations conflict. Configuration cutover does not stop existing host processes or delete TEMP runtimes/backups. Live replacement, reload and dependency proof precede P3-05 retirement; P3-04 separately governs backup disposal.

For a migration, include the deployment choice in the original read-only plan:

```text
python <installed-onboard.py> migration --phase plan --projects-root <absolute-roots> --backup-root <external-private-vault> --custodian <actual-label> --deployment-mode init --deployment-platform codex|omp [--graft-hooks] --json
python <installed-onboard.py> init --platform codex|omp --projects-root <same-roots> --migration-manifest <manifest-file> --migration-apply-receipt <successful-apply-file> --deployment-evidence-out <new-private-file> [--graft-hooks] --yes --json
```

Use `--deployment-mode init-projects` and the `init-projects` entry only for a batch without shared-HOME operations; it cannot install global hooks. The plan seals canonical template sources plus narrowly typed `build-graft` / `configure-graft` operations bound to the installed fixed policy. Unrecognized customized global installation targets block; the current lower-severity limitation concerning unrelated existing Skill-root consumers is recorded in the repository findings ledger, not bypassed here.

Deployment validates the entire manifest/apply/runtime/scope and output path before ordinary installation side effects, then executes only declared resources. It does not run unrelated external installers, migration apply/cleanup or sync. Actual native `graft check` is `smoke-only`, not host-event, full-stack or business-behavior proof.

On retry, explicitly pass `--previous-deployment-evidence <previous-file>` and a new `--deployment-evidence-out`; completed resources retain original before/backup references and are not rewritten. Drift or unknown partial writes stop automatic continuation. The single JSON response contains `deploymentEvidence: {path, evidence}` only for this context; an unsaved/invalid result is null and nonzero, with observed writes retained. The bare saved evidence file is the input to migration verify. Ordinary init has no `deploymentEvidence` field.

## MCP Setup

MCP configuration remains optional and interactive in normal mode. Project-only mode skips it.

Built-in choices:

- Chrome DevTools MCP: `npx -y chrome-devtools-mcp@latest`
- Playwright MCP: when the selected Playwright distribution exposes it, use its bundled `npx playwright mcp` entrypoint; otherwise configure a compatible dedicated Playwright MCP server.
- Maestro MCP: `maestro mcp` with `JAVA_HOME` and `PATH`
- Custom stdio MCP: user-provided command/args/env

The generic MCP menu is separate from the Codex Graft producer described above. The producer binds the verified installed launcher and selected root directly; installation alone does not prove host trust or event execution.

Fixed platform scopes for the generic MCP menu:

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

## Upgrade Alignment

跨平台基线按原始文件字节与相对 POSIX 字符串顺序计算。仓库根 `.gitattributes` 对整个 `sbtd-workflow-onboard/**` 禁用 checkout 文本转换，既保留二进制，也保留上游合法 CRLF；运行时不归一化内容来制造 pin 匹配。Stable promotion 必须从保留上游提交原始字节的 checkout 取证，不能把本地自动换行转换后的内容当作上游原样镜像。

`upgrade` 对显式范围进行内容对齐，不改变 `init` 跳过合法 Skill 壳、`reset` 重装和 `migration` 迁移数据的既有含义。基线来自执行中的完整 Onboard 包：catalog、模板、固定 stable 内容及来源；绝对安装路径或文件时间不是版本。不能证明历史版本时报告 `unknown-drift`，不凭名称或版本字符串猜测。

### 范围与授权

准备 version-1 scope JSON。下例只选择 Skills 与全局规则；路径须替换为真实、明确授权的绝对路径：

```json
{
  "schema_version": 1,
  "skills_roots": ["/abs/selected/skills"],
  "agents_targets": ["/abs/selected/config/AGENTS.md"],
  "hosts": [],
  "shell_profiles": [],
  "decisions": {}
}
```

一个宿主域以 `id`、`platform`、`config_home`、`config`、`skills_roots`、`runtime`（绝对 `python`／`node`／`cli`）和 `project_roots` 描述。宿主 Skills 根也必须在顶层选择。普通 Codex 与 Orca 账户使用各自的配置域，不自动扫描账号或认证目录。Codex／OMP 复用现有受管 Graft 候选生成器；其他平台不擅自新增 Graft 接线。选中已有项目用于验证，不等于初始化项目或构建图授权。

可选 `executable` 是实际宿主 CLI 的绝对路径。`onboard_root` 表示宿主要加载的**已安装 Onboard 包目录**，不是 Skills 根：仅有一个宿主 Skills 根时派生为该根的 `sbtd-workflow-onboard`；多个根必须明确选定其中一个包目录。host-only 范围需显式选定已有且受信的包目录。最终 MCP launcher 指向这个安装目标，不能指向仓库源码或升级暂存执行器。OMP 计划同时核对所选项目的有效继承来源；相同继承连接可复用，来源变化或被禁用／冲突的受管连接不能冒充对齐。

若 OMP 的有效继承来源同时属于本批将改写的 provider 配置，计划／应用以 `inherited-dependency-conflict` 在目标写入前拒绝。先对齐 provider 配置域，再以其实际新状态重新规划 consumer；不把上一份计划中的旧继承快照用作新状态，也不在同一批中先写一半再因自身写入失败。

可选 shell profile 以 `path`、`shell`（`bash`／`zsh`／`powershell`）与绝对 `bin` 描述。仅修改该文件中的受管 PATH 块，保留其他内容；MCP 使用固定绝对运行时，不依赖 PATH。执行 profile 会运行其中用户代码，因此只读计划不启动 shell。

`decisions` 以计划中的绝对目标路径为键，值为 `replace` 或 `preserve`。缺失受管资产进入安装；当前内容跳过；未知内容必须选择后重新计划，先展示额外文件及替换影响。身份不符、不安全路径或候选重叠不能靠 `replace` 放行。保留差异属于例外，不是完全对齐。个人 Skills、Caveman 未知定制、插件、hooks、账号与凭据不在默认升级范围。

### 计划、应用与分层验收

备份根必须是已有私有目录，与安装包及所有目标互不嵌套。默认计划仅 stdout；`--output` 只创建指定私有 vault 内的新计划，不覆盖现存文件。

POSIX 使用当前用户所有权及私有权限证明；Windows 必须有可验证的私有 DACL，`chmod(0700)` 不等于 Windows 隐私证明。已有 vault 只校验、不自动修权限；执行器仅对本次新建的子目录使用既有跨平台私有目录初始化器。准备根目录时须由操作人确认，不能把 plan 变成隐式 ACL 修复。

```bash
python scripts/onboard.py upgrade --phase plan \
  --scope /abs/scope.json --backup-root /abs/private/vault \
  --output /abs/private/vault/upgrade-plan.json --json
```

展示完整计划并确认后，从返回的 `plan.plan_id` 读取 ID（不要让用户手抄 hash）。修改 scope 决策或目标后必须重新生成计划并重新展示。

```bash
python scripts/onboard.py upgrade --phase apply \
  --plan /abs/private/vault/upgrade-plan.json \
  --confirm-plan <plan_id> --yes --json

python scripts/onboard.py upgrade --phase verify \
  --plan /abs/private/vault/upgrade-plan.json \
  --receipt /abs/private/vault/upgrade-receipt-<id>.json --json
```

apply 重新推导范围并校验源、完整前态与私有备份路径，先保存原件，再逐资源写入和测量；写入意图与累计回执供中断后调和。重试必须传入对应 `--receipt`；用户新增或未知后态停止，不通过重新规划丢弃失败事实。Onboard 自身更新由校验后的独立包副本执行，不在被覆盖目录中混合导入新旧模块。跨资源不承诺原子提交；失败报告与原件均保留。

只读 verify 实测当前磁盘，不启动宿主、不构建图、不自动修复。明确批准后可添加 `--probe --yes` 进行运行时与宿主探测。报告分开：

| 层级 | 通过所需证据 | 不可替代的边界 |
|---|---|---|
| disk | 实际完整载荷或受管配置语义匹配固定基线 | 合法 Skill 壳或旧回执不够 |
| runtime | 实际绑定命令及协议能力 | shell 版本号不代表 GUI 使用相同路径 |
| host | 真实 Codex／OMP 进程加载所选受管配置的隔离投影，标记 `isolated-host/selected-projection` | 不是原配置域、GUI 或既有会话重载证明；`live_reload` 保持 unverified |
| legacy | 实际旧入口检测与独立清理结果 | 升级成功不授权删除旧资产 |

`aligned` 仅表示内容对齐；host 未验证必须继续显示未验证。`preserve` 导致 `exceptions`，必需资源不同导致 `drift`；两者非零退出。缺依赖、身份冲突、缺确认或不安全路径为 blocked，执行失败和部分失败保留实际结果。不能把该阶段退出 0 改写成“整机已经与全新安装完全一致”。

当前 `--probe` 的宿主测试不读取认证或发起模型请求，使用临时 HOME 和所选受管配置投影。它证明真实宿主能加载该投影，不证明所有原宿主继承配置或已有连接已切换。原配置域／既有会话是否重载必须另有实际证据；普通 `check` 的 `contentAlignment.scope=skills-only` 只检查所选 Skills 根，不包括全局 AGENTS 或 MCP。

Bash 入口为 `bash install.sh upgrade ...`，PowerShell 为 `./install.ps1 -WorkflowMode upgrade ...`；工作流参数直接转发，不运行普通 onboarding。恢复也由两入口转发。

### 独立恢复与旧资产退出

```bash
python scripts/onboard.py recovery --phase plan \
  --upgrade-plan /abs/private/vault/upgrade-plan.json \
  --upgrade-receipt /abs/private/vault/upgrade-receipt-<id>.json \
  --output /abs/private/vault/recovery-plan.json --json

python scripts/onboard.py recovery --phase apply \
  --upgrade-recovery-plan /abs/private/vault/recovery-plan.json \
  --confirm-recovery <recovery_id> --json
```

恢复只针对本批实际写过的资源，绑定当前实测后态及原件。展示恢复清单后另行确认；后态漂移时保留用户内容并阻断。不自动删除备份，也不承诺恢复旧运行时可用。恢复重试使用返回的累计 `--recovery-receipt`。升级恢复参数不能与 migration 恢复参数混用。

**历史信任边界：** 操作人明确选择且独占管理的已有私有 vault 是受信历史来源。摘要和相互引用验证一致性，不是签名认证；不能防御有 vault 写权限的人整组一致伪造计划、回执、意图与 checkpoint。不得从未知来源接收整套 vault 并据此自动删除文件。来源或控制权存疑时停止恢复，人工核对原件及操作记录。本流程不创建独立签名密钥或后台信任服务。

执行始终绑定当前受信 Onboard 包；包内容在独立升级后变化时，旧计划可能返回 `source-stale`，不会自动信任并执行 vault 内历史代码。保留旧失败证据，使用可信原包核对或重新规划。生成缓存不改变载荷对齐，但恢复仍保护完整当前内容；新增缓存不自动归本批所有。恢复资源后保留空父目录，避免把并发创建的用户目录误删。

九个退役 GitNexus Skills 纳入现有独立 `cleanup-legacy` 身份检测：`gitnexus-cli`、`gitnexus-debugging`、`gitnexus-exploring`、`gitnexus-guide`、`gitnexus-impact-analysis`、`gitnexus-pdg-query`、`gitnexus-pr-review`、`gitnexus-refactoring`、`gitnexus-taint-analysis`。仅在所选根的直接子目录且自身 `SKILL.md` 名称相符时成为候选。没有前缀删除，不卸载 CLI，不删除 `~/.gitnexus`、未选项目索引、历史运行时或备份；清理计划、独立确认和完整原件保护沿用 Cleanup Runtime。

### 升级行为验收场景

本仓库以 Markdown 场景映射现有 unittest，不生成 `.feature`。场景正文中文，结构关键词英文。

| Scenario | Given / When / Then |
|---|---|
| U01 只读完整盘点 | Given 空选定目录；When plan；Then 返回完整 catalog 载荷与摘要，目标和 vault 无新增 |
| U02 合法旧壳不冒充当前 | Given 名称合法但正文或辅助文件不同；When plan；Then 报告缺失、不同、额外文件和未知漂移 |
| U03 升级收敛 | Given 明确替换差异；When apply 后 verify；Then 受管载荷与同基线全新安装等价，原件保留 |
| U04 定制保留 | Given preserve 决定；When verify；Then 报告例外而非完全对齐 |
| U05 多域隔离 | Given 多域与共享根；When apply；Then 共享资源只写一次，未选域不变 |
| U06 前态变化拒绝 | Given 计划后源或目标改变；When apply；Then 不覆盖并报告冲突 |
| U07 重复执行 | Given 上次已完成且后态未变；When 重试或重新计划；Then 不重复改写与制造备份 |
| U08 故障恢复 | Given 部分失败或写后中断；When 续作或确认恢复；Then 记录真实后态且保护原件和用户新增 |
| U09 自升级隔离 | Given 当前包属于更新集合；When apply；Then 独立已校验包执行，载荷不混版 |
| U10 混合配置保护 | Given 其他 MCP 与注释；When 接线；Then 保留无关内容，未知受管所有权拒绝 |
| U11 分层验收 | Given 文件对齐但未有真实宿主证据；When verify；Then disk 与 host 分开，host 不冒报通过 |
| U12 退役身份 | Given 精确旧名及同名异身份目录；When cleanup；Then 仅获批且身份通过者可退出，冲突保留 |
| U13 PATH 与 MCP 分离 | Given 所选 profile；When 确认应用；Then 受管块幂等，MCP 不依赖 shell PATH |
| U14 路径安全 | Given 中文/空格路径或 symlink/junction/重叠目标；When plan/apply；Then 合法路径正确处理，越界拒绝 |
| U15 脱敏输出 | Given 配置含私密字段；When 计划、验证或错误；Then 不打印原始配置或凭据 |
