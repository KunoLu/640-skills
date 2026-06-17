---
name: book-release-readiness
description: Reviews production readiness for services, APIs, jobs, queues, integrations, and deployment-sensitive changes. Use after implementation or during Trellis check when reliability, observability, rollback, or operational failure modes matter.
---

# Book Release Readiness

Use this Skill as a production-readiness pass before considering a service or integration change complete.

It is derived from the `mini` rule style of `agent-rules-books` and complements project validation, TestSprite, Trellis check, and human release review.

## When To Use

- The change affects APIs, background jobs, queues, schedulers, external services, auth, billing, notifications, data pipelines, or deployment behavior.
- Failure modes include timeouts, retries, overload, partial outage, data corruption, duplicate work, or user-visible degradation.
- The task is ready for `$trellis-check` or release review.

Do not use for docs-only changes, local-only scripts, simple UI polish, or code paths that are not production-facing.

## Workflow

1. Identify the production path and the users or systems affected.
2. Check timeouts, retry limits, backoff, cancellation, and duplicate-work safety.
3. Check fallback, graceful degradation, circuit breaking, or isolation where relevant.
4. Check capacity, backpressure, rate limits, and queue growth behavior.
5. Check logs, metrics, traces, alerts, dashboards, and runbook expectations.
6. Check rollout, rollback, feature flag, migration, and cleanup paths.
7. Confirm validation commands and any remaining manual release checks.

## Output

When used inside a Trellis task, record:

- Production risk summary.
- Failure modes covered.
- Observability and alerting notes.
- Rollout and rollback path.
- Validation performed and skipped checks.

Only recurring release standards belong in `.trellis/spec`.

## Guardrails

Do not block completion with theoretical production risks that do not apply to the current project. State residual risk clearly when checks cannot be run.
