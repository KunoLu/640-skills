---
name: book-refactoring-pass
description: Guides behavior-preserving refactoring with small, reversible steps. Use when changing existing code and structural friction, duplication, long functions, tangled responsibilities, or unsafe cleanup could affect the implementation.
---

# Book Refactoring Pass

Use this Skill as a focused refactoring check before or during implementation.

It is derived from the `mini` rule style of `agent-rules-books` and is intended as an on-demand engineering lens, not as a replacement for project rules, tests, Trellis artifacts, GitNexus, or code review.

## When To Use

- Existing code structure is making a requested change risky or awkward.
- A change mixes behavior changes with cleanup.
- Duplication, long functions, feature envy, primitive obsession, or tangled responsibilities are blocking clarity.
- A review needs to decide whether a refactor should happen now or be deferred.

Do not use for simple text, docs, config-only edits, broad rewrites, speculative architecture changes, or code that is already easy to change safely.

## Workflow

1. Identify the observable behavior that must remain unchanged.
2. Confirm the available safety net: tests, characterization checks, manual repro, snapshots, or focused inspection.
3. Separate structural refactoring from behavior changes.
4. Prefer the smallest reversible move that lowers the current task risk.
5. Preserve public contracts unless the task explicitly changes them.
6. Run the project validation appropriate to the touched code.

## Output

When used inside a Trellis task, write only task-specific conclusions to `implement.md`, `design.md`, or the check summary:

- Current friction.
- Behavior that must not change.
- Proposed refactoring steps.
- Safety net and validation command.
- Deferred refactors, if any.

Only long-term conventions belong in `.trellis/spec`.

## Stop Conditions

Stop refactoring when the requested change is safe and clear enough. Do not keep improving code that is outside the task boundary.
