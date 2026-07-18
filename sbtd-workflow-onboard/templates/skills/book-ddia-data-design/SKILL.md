---
name: book-ddia-data-design
description: Guides data-intensive design checks for consistency, reliability, schema evolution, and data flow risks. Use when changing storage, events, queues, caches, replication, migrations, analytics pipelines, or cross-service data ownership.
---

# Book DDIA Data Design

Use this Skill when a change can fail because of data semantics, distributed behavior, or operational reality rather than ordinary code structure.

It is derived from the `mini` rule style of `agent-rules-books` and should complement project architecture, Trellis design, GitNexus impact analysis, tests, and production validation.

## When To Use

- A change affects databases, schemas, migrations, caches, queues, streams, jobs, ETL, analytics, or cross-service APIs.
- The system must handle duplicate messages, retries, partial failure, reordering, eventual consistency, or replay.
- A feature changes data ownership, source of truth, transactional boundaries, or read/write paths.
- Backfill, migration, rollback, or recovery behavior matters.

Do not use for purely local UI work, simple in-memory code, or data changes already covered by clear project conventions.

## Workflow

1. Identify the source of truth and data owner.
2. Map the write path, read path, async path, and failure path.
3. State consistency expectations: strong, eventual, read-your-writes, monotonic reads, or best effort.
4. Check idempotency, ordering, retry, deduplication, and poison-message handling.
5. Check schema compatibility, migrations, backfills, rollback, and replay.
6. Define observability and repair signals for data drift or stuck processing.
7. Validate with focused tests and project validation commands.

## Output

For Trellis tasks, write concise design/check notes:

- Data owner and source of truth.
- Consistency model.
- Failure and recovery behavior.
- Migration/backfill/rollback plan.
- Required tests and validation.

Promote only long-lived data architecture rules to `.trellis/spec`.

## Guardrails

Do not design a distributed system when a local transaction is enough. Keep the model as simple as the project constraints allow.
