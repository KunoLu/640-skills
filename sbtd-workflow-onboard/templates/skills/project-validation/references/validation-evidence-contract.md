# Validation Evidence Contract

Use this contract only when a formal test report is intended to become pull-request evidence or be ingested by a knowledge system. Ordinary local diagnostics and reports that remain local do not need an evidence sidecar.

The native runner report and its same-stem Chinese Markdown summary remain the primary test artifacts. The evidence document is a provenance envelope. It does not replace the report, the summary, or the runner result.

## Source and revision rules

- `developer-local`, `ci`, and `knowledge-server` are separate evidence sources and must never overwrite or masquerade as one another. `ci` means a CI runner created the evidence; it is not an alias for developer-local upload or knowledge-server smoke.
- Record the repository key, raw source ref, full commit SHA when available, worktree state, trigger, and creation time. `branch_slug` is only a filename-safe label; it is not revision identity.
- A dirty developer worktree uses `sourceRevision: dirty` and `evidencePublication: local-only`. It may assist diagnosis, but it cannot attest a PR head.
- Developer evidence used by a PR must use `sourceRevision: exact`, match the current PR head SHA, and be invalidated by every new commit.
- CI evidence uses a clean checkout and `sourceRevision: exact`. When its target is a pull request, the recorded commit must equal the final PR head SHA; a new commit invalidates the evidence and requires a new run or a provider-backed revalidation.
- Evidence created before the final commit records local validation state only. After the commit and before publication or PR Check update, regenerate or revalidate against the final PR head SHA and update the report sidecar or aggregate envelope; pre-commit and older-head evidence cannot attest the PR.
- Knowledge-server evidence must include an exact multi-repository `revisionSet`. A configured branch such as `staging` is resolved to a commit SHA before execution.
- Record whether the runtime environment is aligned with the revisions under test. `unverified` or `mismatch` must not be reported as verified full-stack evidence.
- Preserve the actual test mode. `smoke-only`, `contract-backed`, `mock-backed`, and `app-mocked` evidence cannot be promoted to `full-stack` by publication.

## Feature trace rules

Do not require Feature IDs or Scenario IDs. Each feature source uses repository key, path, optional Feature / Rule / Scenario names, optional Examples fingerprint, source ref, and resolved commit SHA. These fields locate the behavior snapshot without modifying the `.feature` file.

## Artifact rules

- Place a per-report sidecar next to the formal report using the same report stem plus `.evidence.json`, for example `playwright-report-order-staging-2026_07_15-12_00_00.evidence.json`.
- A cross-tool orchestrator may instead create one envelope in its isolated runtime or evidence bundle, provided it references every report and summary.
- Every referenced formal report records its path, same-stem Markdown summary path, SHA-256 digest, status, test type, and actual execution mode.
- Evidence publication must redact secrets, tokens, accounts, PII, sensitive request data, production data, screenshots, traces, and attachments before upload.
- `published` means the envelope and referenced artifacts were accepted by the configured evidence destination. It does not mean the tests passed.
- CI publication is separate from CI execution: use `published` only after the PR or knowledge destination accepts the evidence, `not-configured` when no publisher exists, and `blocked` when publication was required but failed. CI evidence cannot use `local-only`.

## Required status output

- `Evidence Source`: `developer-local` / `ci` / `knowledge-server` / `not-needed`
- `Source Revision`: `exact` / `dirty` / `unknown` / `not-needed`
- `Environment Alignment`: `verified` / `unverified` / `mismatch` / `not-needed`
- `Evidence Publication`: `local-only` / `published` / `blocked` / `not-configured` / `not-needed`

Validate machine-readable envelopes with `validation-evidence.schema.json`. Storage, publishing commands, PR provider adapters, retention, and server orchestration are outside the P0 contract and belong to later integration phases.
