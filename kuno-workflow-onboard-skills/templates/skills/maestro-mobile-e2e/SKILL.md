---
name: maestro-mobile-e2e
description: Use when generating or running Maestro Mobile/Hybrid E2E flows, deriving Maestro YAML from BDD `.feature` scenarios, configuring Maestro report paths, or debugging Maestro iOS real-device runs.
---

# Maestro Mobile E2E

Use this Skill for Mobile / Hybrid E2E work that uses Maestro.

This Skill does not replace `gherkin-bdd`, `project-validation`, Trellis, project tests, or human review. BDD `.feature` files are the behavior source of truth; Maestro flow YAML files are executable Mobile / Hybrid E2E assets derived from selected BDD scenarios.

## Workflow

1. Confirm the task involves Android, iOS, React Native, Flutter, Hybrid App, mobile smoke, or cross-device user journeys.
2. Read the relevant BDD `.feature` scenarios first. If no BDD scenario exists for user-visible behavior, return to `gherkin-bdd` before generating flow assets.
3. Decide whether the BDD scenario should become a Maestro flow. Use Maestro for device-level journeys, native permissions, deep links, system UI, mobile navigation, or Hybrid flows that cannot be covered reliably by Web E2E alone.
4. Generate or update flow assets under `maestro/flow/`.
5. Before running Maestro, confirm Java 17+, Maestro CLI, target device / simulator, app binary or installed app, bundle id / app id, test account, and environment.
6. Run the smallest relevant flow first. Expand to `smoke.yml` only after the targeted flow is stable.
7. If an iOS real-device failure matches the known issue index, load the matching reference and apply only the relevant fix before rerunning the smallest failing flow.
8. Report flow asset paths, commands, report files, artifacts location, blocked items, and remaining risk.

## Flow Asset Contract

- Store repo-resident Maestro flows in `maestro/flow/`.
- Use `.yml` extension.
- Use English names for both file names and Maestro `name` fields.
- Use lower-kebab-case file names for business scenarios, for example `maestro/flow/login-success.yml`.
- Use `maestro/flow/smoke.yml` for the full regression / smoke flow only.
- Keep one maintainable flow per business scenario unless the project already has a stronger Maestro architecture.
- Add a short trace comment near the top of generated flows that points back to the source BDD feature path and scenario name.
- Do not generate fragile flows when stable selectors, deterministic data, app launch state, permissions, or test accounts are unavailable. Report `Maestro Flow Assets: blocked` with the missing prerequisite.

Example flow header:

```yaml
appId: com.example.app
name: Login Success
tags:
  - mobile
  - smoke
---
# BDD: features/authentication/login.feature :: Scenario: 已注册用户使用正确密码登录
- launchApp
- tapOn: "Email"
- inputText: "${MAESTRO_TEST_EMAIL}"
- tapOn: "Password"
- inputText: "${MAESTRO_TEST_PASSWORD}"
- tapOn: "Login"
- assertVisible: "Home"
```

## BDD To Flow Mapping

- Map `Given` to deterministic app state, fixtures, launch arguments, deep links, or setup steps.
- Map `When` to user actions such as `tapOn`, `inputText`, `scrollUntilVisible`, `back`, `swipe`, or nested subflows.
- Map `Then` to visible, accessible, persisted, or emitted outcomes such as `assertVisible`, `assertNotVisible`, or stable post-action screen state.
- Prefer accessibility identifiers and stable user-visible labels. If the app lacks stable selectors for critical controls, propose the minimal selector addition and stop unless the user has approved product code changes.
- Keep secrets out of flow files. Use environment variables or project-approved test secret injection.
- Use nested flows only when they remove real duplication and remain readable.

## Report Contract

When Maestro JUnit or HTML reports are generated, write them under `.maestro/reports/` in the project root.

Use this timestamp shape in local time:

```text
YYYY_mm_dd-HH_MM_SS
```

Report file names:

```text
.maestro/reports/maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.xml
.maestro/reports/maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.html
```

`flow_name` is the flow file stem, such as `login-success` or `smoke`.

Example commands:

```bash
mkdir -p .maestro/reports
flow=maestro/flow/login-success.yml
flow_name=$(basename "$flow" .yml)
stamp=$(date +%Y_%m_%d-%H_%M_%S)
maestro test --format junit --output ".maestro/reports/maestro-report-${flow_name}-${stamp}.xml" "$flow"
maestro test --format html --output ".maestro/reports/maestro-report-${flow_name}-${stamp}.html" "$flow"
```

If both JUnit and HTML are required and the Maestro CLI cannot emit both formats in one run, run two explicit commands or explain the project-specific reporter limitation. Do not claim both report files exist until the files are present.

Maestro runtime artifacts still default outside the repository under `~/.maestro/tests` on macOS / Linux unless the command or project config overrides the output directory. Do not treat `~/.maestro/tests` as a repo asset.

## Known Issue Index

Known issue references are lazily loaded. Do not read reference files preemptively.

Read `references/lessons-index.md` only when a Maestro run, setup, or device inspection fails. Then load the referenced file only if tags, keywords, error messages, platform, or version match the current failure.

Current reference topics include:

- iOS real-device setup and Maestro 2.6.1 driver issues.

## Output

Report:

- `Maestro Flow Assets`: `generated` / `reused` / `blocked` / `skipped`.
- Flow files created or updated under `maestro/flow/`.
- Source `.feature` paths and scenario names traced by each flow.
- Maestro CLI / MCP / Java / device status.
- Commands run and whether reports were generated.
- Report paths under `.maestro/reports/`.
- Runtime artifact location, usually `~/.maestro/tests`.
- Known issue reference loaded, fix applied, restore command if a tool patch was made, and rerun result.
- Remaining manual setup, account, environment, selector, device, signing, or toolchain risks.
