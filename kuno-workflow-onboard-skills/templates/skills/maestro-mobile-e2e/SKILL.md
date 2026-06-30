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
3. Run the mobile context gate before generating or running flows.
4. Decide whether the BDD scenario should become a Maestro flow. Use Maestro for device-level journeys, native permissions, deep links, system UI, mobile navigation, or Hybrid flows that cannot be covered reliably by Web E2E alone.
5. Classify the run mode: `full-stack`, `contract-backed`, `app-mocked`, `smoke-only`, or `blocked`.
6. Generate or update flow assets under `maestro/flow/`.
7. Before running Maestro, confirm Java 17+, Maestro CLI, target device / simulator, app binary or installed app, bundle id / app id, test account, and environment.
8. Run the smallest relevant flow first. Expand to platform smoke or full regression only after the targeted flow is stable.
9. If an iOS real-device failure matches the known issue index, load the matching reference and apply only the relevant fix before rerunning the smallest failing flow.
10. After failures are fixed and targeted reruns pass, run the planned final full validation and generate one final passing report plus one Markdown run summary.
11. Report flow asset paths, commands, report files, artifacts location, blocked items, and remaining risk.

## Mobile Context Gate

Before writing or running a flow, confirm:

- Platform scope: `ios`, `android`, `both`, or `hybrid`.
- App artifact: `.app`, `.ipa`, `.apk`, installed app, simulator / emulator build, or cloud build.
- App identity: iOS bundle id and / or Android application id.
- Target: iOS Simulator, iOS real device, Android Emulator, Android real device, or cloud device.
- Backend dependency: live environment, mock environment, contract-only backend, or missing backend.
- App launch control: base URL override, launch arguments, deep link, feature flags, clear-state strategy, and deterministic starting screen.
- Data and accounts: test account, role, seed data, cleanup strategy, and environment isolation.
- Selectors: stable accessibility identifiers, stable labels, platform differences, and WebView boundary strategy when applicable.
- System capabilities: permissions, camera, photos, location, notifications, file picker, external app hops, OS dialogs, and native login.

If required context is missing, do not generate a fragile flow. Report `Maestro Flow Assets: blocked` and list the missing facts. Mock-backed or app-mocked flows are allowed only when behavior comes from a contract, real sample, existing fixture, launch argument, or explicit user confirmation; they must not be reported as full-stack E2E.

## Flow Asset Contract

- Store repo-resident Maestro flows in `maestro/flow/`.
- Use `.yml` extension.
- Use English names for both file names and Maestro `name` fields.
- Use lower-kebab-case file names for business scenarios, for example `maestro/flow/login-success.yml`.
- Use `maestro/flow/smoke.yml` for the full regression / smoke flow only.
- When iOS and Android need materially different flows, use platform subdirectories such as `maestro/flow/ios/login-success.yml` and `maestro/flow/android/login-success.yml`; platform smoke flows may use `maestro/flow/ios/smoke.yml` and `maestro/flow/android/smoke.yml`.
- Keep one maintainable flow per business scenario unless the project already has a stronger Maestro architecture.
- Add a short trace comment near the top of generated flows that points back to the source BDD feature path, scenario name, platform scope, and run mode.
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
# Platform: ios
# Mode: full-stack
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

When the final planned Maestro validation passes, write one formal native report under `.maestro/reports/` in the project root, plus one Markdown run summary with the same stem and timestamp. Debugging and targeted rerun output may use stdout or temporary artifacts, but do not create multiple formal reports for intermediate failed rounds.

Use this timestamp shape in local time:

```text
YYYY_mm_dd-HH_MM_SS
```

Report file names:

```text
.maestro/reports/maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.xml
.maestro/reports/maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.html
.maestro/reports/maestro-report-{flow_name}-{YYYY_mm_dd}-{HH_MM_SS}.md
```

`flow_name` is the flow file stem, such as `login-success` or `smoke`. Keep `flow_name` in the report file name even when the flow is derived from a BDD `.feature`; the Markdown summary records the source `.feature` path and scenario name.

Example commands:

```bash
mkdir -p .maestro/reports
flow=maestro/flow/login-success.yml
flow_name=$(basename "$flow" .yml)
stamp=$(date +%Y_%m_%d-%H_%M_%S)
maestro test --format junit --output ".maestro/reports/maestro-report-${flow_name}-${stamp}.xml" "$flow"
```

Use the project-required native reporter. Default to JUnit when CI needs machine-readable output; use HTML only when the project or user asks for human-readable local reports. If project configuration forces multiple reporters, treat them as one final report set from the same final passing run, and still generate only one Markdown summary.

The Markdown summary must include platform scope, run mode, mock strategy, executed case / flow list, source `.feature` path and scenario name for each flow, final report path, total rounds, each round command, failed case / flow, failure classification, fix summary, changed files, targeted rerun result, affected subset rerun result, final full rerun result, skipped items, and remaining risk. Do not include real accounts, secrets, PII, production data, full tokens, sensitive headers, or production screenshots.

## Failure Rerun Loop

On failure:

1. Classify the failure as app code, test code, BDD / spec, mock / contract drift, environment / account / data / device, flaky / timing, or out-of-scope.
2. If the issue is in scope and fixable, apply the smallest fix.
3. Rerun the failed flow first.
4. After the failed flow passes, rerun the affected platform subset, such as the same platform smoke flow or related business flow.
5. Run the planned final full validation before generating the formal report and Markdown summary.
6. If fail-fast stopped on the first failure, do not assume later flows passed; continue with unrun flows or rerun the planned final validation.

Maestro runtime artifacts still default outside the repository under `~/.maestro/tests` on macOS / Linux unless the command or project config overrides the output directory. Do not treat `~/.maestro/tests` as a repo asset.

## Known Issue Index

Known issue references are lazily loaded. Do not read reference files preemptively.

Read `references/lessons-index.md` only when a Maestro run, setup, or device inspection fails. Then load the referenced file only if tags, keywords, error messages, platform, or version match the current failure.

Current reference topics include:

- iOS real-device setup and Maestro 2.6.1 driver issues.

## Output

Report:

- `Maestro Flow Assets`: `generated` / `reused` / `blocked` / `skipped`.
- `Mobile Platform Scope`: `ios` / `android` / `both` / `hybrid` / `not-needed`.
- `Mobile E2E Mode`: `full-stack` / `contract-backed` / `app-mocked` / `smoke-only` / `blocked`.
- `Mock Strategy`: `none` / `contract-backed` / `user-approved` / `blocked`.
- Flow files created or updated under `maestro/flow/`.
- Source `.feature` paths and scenario names traced by each flow.
- Maestro CLI / MCP / Java / device status.
- Commands run and whether reports were generated.
- Report paths under `.maestro/reports/`.
- `Run Summary MD`: Markdown run summary path under `.maestro/reports/`.
- Targeted rerun, affected subset rerun, and final full rerun results.
- Runtime artifact location, usually `~/.maestro/tests`.
- Known issue reference loaded, fix applied, restore command if a tool patch was made, and rerun result.
- Remaining manual setup, account, environment, selector, device, signing, or toolchain risks.
