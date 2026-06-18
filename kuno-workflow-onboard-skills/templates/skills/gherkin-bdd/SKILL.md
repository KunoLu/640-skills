---
name: gherkin-bdd
description: Use when adding, changing, reviewing, or testing user-visible behavior with BDD, Gherkin, Given/When/Then scenarios, .feature files, acceptance criteria, or bug-fix behavior specs.
---

# Gherkin BDD

Use this Skill for user-visible behavior. BDD is a default hard rule: new or changed behavior that a user, administrator, API client, CLI user, integration system, exported file consumer, notification recipient, or permission/error-state observer can see must have a persistent BDD scenario before implementation is completed.

BDD does not replace PRD, DDD, TDD, project validation, or Trellis. It turns confirmed acceptance behavior into executable examples. PRD explains intent and scope, DDD stabilizes vocabulary and boundaries, BDD specifies observable behavior, and TDD turns the scenario into red tests and green implementation.

## When To Use

Use this Skill when:

- The user asks for BDD, Gherkin, Given/When/Then, `.feature`, scenarios, acceptance criteria, or behavior specs.
- A task adds or changes UI, API, CLI, exported files, notifications, permissions, errors, status changes, or externally observable integration behavior.
- A user-visible bug is being fixed.
- A Trellis task has acceptance criteria that describe user-visible behavior.
- Existing code needs BDD coverage backfilled for touched behavior.

Skip BDD only when the change is not user-visible, such as internal refactoring, dependency or tool configuration, purely mechanical formatting, or visual/text-only polish that does not change behavior or meaning. When skipping after code changes, report the reason.

## Persistent Spec Location

Project conventions win:

1. If the project already has `.feature` files, a `features/` directory, or BDD runner configuration, follow the existing path, language, and naming style.
2. Otherwise, single-application projects use `<project-root>/features/<capability-slug>.feature`.
3. Larger projects may group by capability area, such as `features/authentication/login.feature` or `features/orders/order-cancellation.feature`.
4. Monorepos use the owning workspace root, such as `apps/web/features/checkout/cart-update.feature`, `services/billing/features/invoice-export.feature`, or `packages/cli/features/project-init.feature`.
5. Cross-package behavior belongs near the product entry point that owns the observable capability, not in every internal package.

Trellis task artifacts can draft or reference scenarios, but they are not the default long-term behavior source of truth. Use another persistent BDD path only when project-level rules explicitly define it.

## Language Rules

- Existing `.feature` files define the language and keyword style for their bounded context or feature area.
- If no `.feature` files exist, write scenario titles, descriptions, and step text in Simplified Chinese by default.
- Use English Gherkin structural keywords by default: `Feature`, `Rule`, `Background`, `Scenario`, `Scenario Outline`, `Examples`, `Given`, `When`, `Then`, `And`, and `But`.
- Do not add `# language: zh-CN` when using English Gherkin keywords. Add it only when the project already uses localized Chinese Gherkin keywords or the user explicitly requests them.
- Avoid mixing keyword languages inside the same bounded context or feature area.
- Domain terms must follow the project glossary, `docs/CONTEXT.md`, context docs, `.trellis/spec`, and existing scenario vocabulary.

Before creating or rewriting a `.feature` file, make an explicit language decision:

1. Inspect existing `.feature` files, BDD runner configuration, and project-level BDD rules.
2. If matching `.feature` files already exist, follow the nearest bounded context or feature area language and keyword style.
3. If no `.feature` files exist and the user did not request another language, set scenario text language to Simplified Chinese, Gherkin keyword language to English, and omit `# language: zh-CN`.
4. Report the chosen scenario text language and keyword language before writing or patching the file.

Do not infer English scenario text merely from English Gherkin keywords, English PRD / design documents, code identifiers, package names, or product names. Proper nouns and established domain terms may remain in their project vocabulary inside Chinese sentences.

Default first-file pattern:

```gherkin
Feature: 用户登录
  用户需要使用账号进入工作区，以便继续管理自己的配置。

  Scenario: 已注册用户使用正确密码登录
    Given 用户已经注册账号
    When 用户提交正确的邮箱和密码
    Then 用户进入自己的工作区
    And 页面显示当前登录状态
```

## Scenario Rules

Write scenarios as product behavior, not implementation:

- Name `Feature` after the user-visible capability, not the implementation component.
- Use one behavior per scenario.
- Make scenarios independent and chronologically executable.
- `Given` states relevant preconditions.
- `When` states one user or system action.
- `Then` states visible, persisted, returned, emitted, or otherwise externally observable outcomes.
- Prefer concrete, realistic examples over placeholders.
- Keep step text free of selectors, mocks, fixtures, database fields, internal function names, and test helper names unless the behavior is inherently at that layer.
- Use `Rule` only for a policy or invariant shared by multiple scenarios.
- Keep `Background` short and only for facts true for every scenario in the file.
- Use `Scenario Outline` only when an examples table covers the same behavior with meaningful input variations.

For user-visible wording or UI changes, require scenarios when the change affects meaning, decisions, validation, status, permissions, flow, defaults, or accessibility semantics. Skip scenarios for typos, spacing, color polish, token/class rewrites, or layout cleanup that does not change behavior or meaning.

## Workflow

1. Decide whether the change is user-visible. If yes, BDD applies.
2. Read existing `.feature` files and project vocabulary before drafting.
3. Run the language decision gate and report the chosen scenario text language and Gherkin keyword language.
4. If domain terms or boundaries are unclear, use `grill-with-docs` and `book-ddd-distilled-modeling` before finalizing scenario wording.
5. Create or update the persistent `.feature` file before implementation.
6. Review scenarios for observable behavior, one-behavior focus, vocabulary consistency, realistic examples, absence of implementation details, and compliance with the language decision.
7. Derive tests from scenarios. If the project has a Gherkin runner, bind scenarios to step definitions or runner tests. Otherwise use the existing test framework and make each test traceable to a scenario by name, comment, file organization, or the project's established convention.
8. For new behavior or bug fixes, run the derived test first and confirm it fails for the intended behavior before implementation.
9. Implement the smallest change that makes the scenario-backed tests pass.
10. During validation, confirm PRD, `.feature`, tests, and code agree.

If a scenario cannot be automated yet, tag it `@todo` or the project's equivalent marker and add an adjacent comment explaining the blocker and temporary manual verification. Do not silently drop it.

## Existing Code Backfill

For existing projects, use `no new uncovered behavior`:

- New user-visible behavior must have BDD coverage before implementation.
- Touched existing behavior must get or update relevant scenarios.
- User-visible bug fixes first add the correct behavior scenario, then a failing regression test, then the fix.
- Untouched legacy behavior can remain uncovered until it is changed or an explicit BDD migration is requested.

When backfilling from code, record what the code does today in product language. If behavior appears suspicious or contradicts docs, names, comments, tests, or obvious user expectation, ask whether it is intended. If it is a defect, write the intended behavior as the scenario and let the derived test go red.

## Source Of Truth

For confirmed user-visible behavior, the persistent `.feature` file is the behavior source of truth.

- `prd.md` holds background, scope, constraints, non-goals, and acceptance intent.
- `.feature` holds the testable behavior examples.
- `design.md` and `implement.md` hold technical decisions and plans.
- Tests prove the implementation matches the scenarios.

If PRD, Trellis artifacts, `.feature`, tests, and code disagree, do not implement through the conflict. First align the PRD and `.feature`, then adjust tests and code.

## Output

When drafting or updating BDD specs, report:

- Feature files created or updated.
- BDD language decision: scenario text language, Gherkin keyword language, and whether it follows existing project convention or the first-file default.
- Scenarios added, changed, removed, or marked `@todo`.
- How each scenario is or will be traced to automated tests.
- Any BDD skip decision and reason.
- Any conflict found between PRD, existing `.feature`, tests, and code.
