# Task state and recovery

Use this reference only when reading or changing persistent task state. Pure questions and explicit read-only work keep state in conversation and perform no task/pointer/handoff/identity/ignore writes.

## One effective record

The task's `task.md` owns mode, source, status, timestamps, body and events. Ordinary default tasks use `.sbtd/tasks/<logical-id>/task.md`; lite/strict use `ai/tasks/<logical-id>/task.md`. Explicit sharing can promote a default task without changing its mode. Switching down never deletes shared history.

`.sbtd/active-task.json` is only `{schema_version, task_id, task_path}`. A shared `ai/tasks/index.md` is navigation; handoff is a dated snapshot. Neither owns a second mode or status. Local files do not automatically move to another machine or worktree.

Before any local write, inspect actual ignore rules and tracked state. If `.sbtd` or `docs/handoffs` lacks protection, request narrow authorization for the required root-anchored rules; do not initialize an entire project or remove old protection. A reserved path that contains user content is a conflict, not permission to hide or replace it. No authorization means no local persistence; say so and continue only unrelated safe work where the mode permits.

## Read and validate

1. Resolve the explicit task or current valid bookmark inside the authorized project. Do not scan unrelated projects or choose the newest file. Multiple candidates require a task choice before asking about that task's missing mode.
2. Inspect the full task and relevant events before changing it. Use [task-data.schema.json](task-data.schema.json) for the normalized frontmatter, active pointer and event shapes. Core version is integer 1; unknown versions are not silently interpreted. Validate timestamps with actual calendar/timezone parsing: a format annotation without a registered assertion is not a check.
3. Safely parse UTF-8/JSON-compatible YAML without executing tags, objects or commands. Reject duplicate keys, cycles and nonfinite values. Preserve unrelated body and extension data; an unsupported extension or parser must not lead to silent data loss.
4. Check actual filesystem containment and types, including every relevant parent and symlink. Lexical schema checks do not prove containment. Active paths must resolve under this project's `.sbtd/tasks/` or `ai/tasks/`, end at task.md and match the record's full logical ID. Archive paths may differ from the ID; basename equality is not identity.
5. Require unique IDs, resolvable parents and an acyclic parent graph. A parent may summarize in-progress children, but multiple executable leaves do not share one writer. Preserve a logical ID through promotion and archive.
6. Compare the task's branch/root with the actual checkout. A different ordinary branch, detached binding or Git/non-Git mismatch requires correct-worktree, explicit rebinding or read-only choice. Normal new commits on the same ordinary branch do not alone constitute a branch conflict. Missing historical SHA stays unknown.
7. Effective mode comes from the current explicit user choice, otherwise the selected task. Use `mode_source=default` only for a new implicit default; an explicit user choice or accepted recommendation uses `user`, even when the chosen mode is default. Preserve choices and refusals in `mode_note` where writing is allowed. `migration-unknown` pairs with null mode until the user chooses; do not assume a legacy task was strict. Do not use an old handoff to overwrite a current choice.

A missing optional checker does not grant permission to claim it ran. Use available tools for the actual validation, or report exactly which writes/claims remain unsafe. Strict required verification cannot be marked passed by inspection alone when executable proof is required.

## Write one task

Before writing, confirm the operation, authorization, branch and expected old content. Use one writer. Produce a complete candidate, validate it, and replace the task through a same-directory temporary file/atomic replacement when supported. Where a tool cannot guarantee the required safe replacement, do not pretend it can; preserve the original and stop that write. Unexpected concurrent edits are a conflict, not permission to force overwrite.

Core fields and an event that belongs to this operation must change together in the same task.md. The schema permits some historical unknown values, but a new task or operation needs actual timestamps and evidence. Unknown historical completion time remains null with its source explained; do not use today's time as its old completion time. Preserve the original legacy evidence separately under its migration policy.

A status change uses the documented lifecycle: planned → in-progress → checking → done; checking may return to in-progress; unfinished work may block; done reopens to planned. Do not infer completion from a directory name or a successful command unrelated to acceptance.

A completed task records a completion event whose `at` equals `completed_at`. Reopening first preserves the original completion event/time/evidence, then appends done→planned and clears the current completed_at. Reopen completed ancestors before the child; cross-file writes are not a transaction. On partial failure, report the actual completed steps and stop the remaining ones.

## Events and blocked recovery

Use the task body's single `## 状态事件` table, created when one of these meaningful events occurs:

| at | from | to | reason | evidence |
|---|---|---|---|---|

Reasons and evidence must be nonempty and safe for Markdown. Escape cell delimiters/newlines without losing meaning. Missing historical evidence is `not-recorded` with an explanation, not an invented path. Private credentials, accounts or source hashes do not belong in a shared event table.

- New block: validate `blockEntryEvent`, which requires an actual timestamp and from planned/in-progress/checking. Set status, blocked_reason and updated_at with that event.
- Continuing block: update the reason/time only. Do not append a new blocked→blocked ingress or replace the saved previous phase.
- Archive or explicitly authorized rebinding can record identical from/to states, including blocked→blocked. Validate `stateEvent`, but require a real corresponding operation; this is not an ingress and must not reset recovery history.
- Recovery pairs genuine ingress and release events and selects the latest unmatched ingress. Restore its real from value, only planned/in-progress/checking; clear blocked_reason and append the release event. A mode change or metadata self-transition does not change this match.
- If the historical chain is missing, contradictory or cannot prove the previous phase, ask for the recovery phase, explain that the old phase is unknown, and preserve existing records. Do not invent ingress, guess from mode or return directly to done.
- `from=unknown,to=done` is only for substantiated old completion whose previous state is unavailable. `at=unknown` is only historical. Neither is a shortcut for a new completion.

On a retry, compare actual content and events: an already-completed identical operation is not appended again. Event history is not a separate journal service and does not supply concurrency isolation or authorization by itself.

## Promotion, archive and handoff

Promote with the same format and ID: write/validate target candidate, update effective reference and necessary shared index, then retire the old local record only after confirmation. Preserve originals and recovery information until the handover is proven. Do not write both copies or select by mtime; reconcile explicit references and user modifications after interruption.

Archive only after confirmation, preserving the complete directory/events. Shared completed tasks use `ai/tasks/archive/YYYY-QN/` from a reliable completion date; unknown dates use `undated`. Archiving local data does not authorize publishing it or deleting backups.

When a real continuation event occurs, use [handoff.md](handoff.md). After a successful status operation, update only the navigation the task needs and report what actually persisted. Damaged state does not justify creating a same-name replacement; default/lite can continue unrelated safe work, while strict required artifacts remain incomplete.
