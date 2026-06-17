---
name: book-ddd-distilled-modeling
description: Guides lightweight domain modeling with ubiquitous language, bounded contexts, and subdomain focus. Use before PRD, design, or implementation when requirements involve business terminology, domain rules, context boundaries, or model ambiguity.
---

# Book DDD Distilled Modeling

Use this Skill to sharpen domain language before turning a business request into PRD, issues, design, or code.

It is derived from the `mini` rule style of `agent-rules-books` and should run after project evidence is read. It complements `grill-with-docs`, `to-prd`, and Trellis planning.

## When To Use

- A requirement uses business terms that may mean different things in different parts of the system.
- A change touches domain rules, permissions, lifecycle, workflow state, billing, identity, tenancy, inventory, orders, subscriptions, or similar concepts.
- It is unclear whether two concepts belong in the same model or bounded context.
- A PRD or design needs stable terminology before implementation.

Do not use for purely technical refactors, simple UI copy, mechanical dependency updates, or features with no domain ambiguity.

## Workflow

1. Read existing project facts first: README, domain docs, `.trellis/spec`, ADRs, task artifacts, and relevant code.
2. List the key terms and their current meanings in the project.
3. Identify bounded contexts where the same word may have different meanings.
4. Distinguish core, supporting, and generic subdomains when that affects priority or design.
5. State invariants and business rules in the language used by the project.
6. Feed the agreed language into `prd.md`, `design.md`, or `implement.md`.

## Output

Record concise task-level output:

- Ubiquitous language terms.
- Bounded context assumptions.
- Invariants and rules.
- Open domain questions.
- Terms that should not be used interchangeably.

Only stable, cross-task domain decisions should be promoted to `docs/CONTEXT.md`, ADRs, or `.trellis/spec`.

## Guardrails

Do not force DDD ceremony into small tasks. Prefer just enough language and boundaries to make the current decision safe.
