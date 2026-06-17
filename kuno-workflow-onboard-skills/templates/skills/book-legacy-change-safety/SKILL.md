---
name: book-legacy-change-safety
description: Guides safe changes to legacy or weakly tested code by characterizing behavior before editing. Use when fixing bugs or changing code with unclear behavior, low test coverage, hidden dependencies, or high regression risk.
---

# Book Legacy Change Safety

Use this Skill when the main risk is not the requested change itself, but the uncertainty around existing behavior.

It is derived from the `mini` rule style of `agent-rules-books` and is intended to complement `diagnose`, `tdd`, GitNexus impact analysis, and project validation.

## When To Use

- The target code has weak or missing tests.
- The current behavior is unclear, accidental, or undocumented.
- Dependencies are hidden behind globals, singletons, network calls, files, time, randomness, or external services.
- A bug fix could change behavior that other callers rely on.

Do not use for cleanly tested new code, docs-only work, or simple isolated edits with obvious behavior and low blast radius.

## Workflow

1. State the exact behavior to change.
2. State the behavior that must be preserved.
3. Reproduce the current behavior before editing.
4. Add the smallest useful safety net, such as a characterization test, focused unit test, integration check, or manual script.
5. Introduce a seam only when needed to isolate a hard dependency.
6. Make the smallest behavior change that satisfies the task.
7. Run focused tests first, then the project validation required by the changed area.

## Output

When used inside a Trellis task, record:

- Current observed behavior.
- Preserved behavior.
- Added or chosen safety net.
- Dependency seam, if introduced.
- Validation command and result.

If a lesson is learned because a regression, tool mistake, or workflow error occurred, use `lessons-record`; otherwise do not create a lesson.

## Guardrails

Do not rewrite legacy code just to make it nicer. Stabilize first, change second, improve only where the current task needs it.
