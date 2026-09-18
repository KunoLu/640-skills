# Handoff and continuation

Use handoff for a real pause, clear/context switch, branch switch with unfinished work, actual context pressure or an explicit continuation need. Tool-call/status-update counts and entering checking are not triggers. Do not create a handoff for every finished task or refresh an unchanged snapshot.

## Runtime helper

Persist and read handoffs with `HandoffStore` from `scripts/sbtd_handoff.py` in the installed Onboard Skill copy, built over the project's `TaskStore` and reusing its protected atomic writes and controlled Git environment. It is a host-native library, not a new CLI, daemon, journal or scheduler; if the installed helper copy or its declared dependencies are unavailable, say that persistence did not run. `HandoffPolicy(task_opt_out=False, session_opt_out=False)` carries the two latched opt-outs as explicit flags; the store never mutates it, and a session opt-out is reported before a task opt-out.

`save(task_id, content=..., trigger=..., policy=..., confirmed=False, redaction_confirmed=False)` returns a `HandoffResult` with `status`, `persisted` and, when applicable, `path`, `snapshot` and `reason`:

- `suppressed` — the trigger is outside the pause / context-switch / branch-switch / context-pressure / manual allowlist (status counts and entering checking included), or an automatic trigger hit a latched opt-out; nothing is written. A `manual` trigger ignores the opt-outs without clearing either flag.
- `conversation-only` — a read-only store, even for `manual`; state that cross-session restoration was not persisted.
- `branch-conflict` — the task record's branch differs from the current binding; zero writes and the recorded actual mode is preserved in the result.
- `unprotected` — `docs/handoffs/` is not ignored; a tracked or unverifiable protection state raises `TaskStateError` instead.
- `unchanged` — an identical meaningful snapshot is already persisted; the comparison covers every field including status, mode, HEAD, policy and content and excludes only `created_at`, so crossing a day alone never rewrites. The result is `persisted=True` with the existing path.
- `pending-confirmation` — `confirmed=False`; the planned snapshot is returned and nothing is written. `needs-redaction` — confirmed but without the explicit `redaction_confirmed`. `saved` — the snapshot was atomically written. The helper never overwrites another user's file.

`protect(confirmed=False)` returns True when it appends the root-anchored `/docs/handoffs/` rule and False when protection already exists; it raises `TaskStateError` for a read-only store, a missing confirmation, tracked state or a rule that would hide unknown existing data. On a genuinely non-Git root the rule is inserted before a final `/.sbtd/` rule so both protections stay valid; the helper never initializes Git. `load(relative_path)` strictly parses only owned snapshots — closed shape with `schema_version` 1, the filename hex decoding to the frontmatter `task_id`, and `project_root` equal to this root; malformed, unowned or foreign files raise `TaskStateError`. Snapshots of any age load fine and never change the task. `reminders(now=None)` returns only snapshots at most seven days old, latest per task, whose root and current branch binding match and whose task is unfinished; malformed or foreign files are skipped. No automatic session-start read exists without an observed host capability.

## Before saving

1. Honor task- and session-level auto-handoff opt-outs. “本任务不要自动交接” sets the task opt-out; “本会话关闭自动交接” sets the session opt-out. Keep each latched across continuation until the user explicitly requests “本任务恢复自动交接” or “本会话恢复自动交接” for that scope; clearing the task flag cannot override a session opt-out. Equivalent explicit wording is valid. An explicit manual request can still be fulfilled without clearing either flag. `normal mode` is a presentation instruction, not an SBTD execution-mode or handoff-policy switch.
2. Explicit read-only scope means the handoff stays in the conversation; do not write even an existing file. State that cross-session restoration was not persisted.
3. For a writable handoff, first verify the authorized project and real ignore/tracked protection for `docs/handoffs`. Missing protection needs the narrow authorization described in [state.md](state.md), not automatic initialization or broad ignore changes.
4. Prefer the current task record. Handoff is a snapshot, never the second source of mode/status or a replacement for saving the original mode choice.

## Content and path

Use `docs/handoffs/{YYYY_mm_dd}-{hex}.md`, where the key is the lowercase hex of the UTF-8 full logical task ID including every parent segment — collision-free even for case-differing IDs on case-insensitive filesystems, OS-safe and reversible; never use a child basename, a lossy slug, or the file name as authority. Update the same task/day file only when information actually changed; crossing a day does not alone require a handoff.

Record only factual continuation context:

- Full task ID and effective record path; selected mode, source and any refused recommendation.
- Project/branch and observed full HEAD, or explicit unknown; snapshot time.
- Goal, accepted decisions, completed work and remaining work.
- Changed files, actual commands/results, meaningful failures and rejected approaches.
- Next concrete action, missing facts/permissions, and operations not to repeat.
- Active auto-handoff/presentation opt-outs and observable session state needed for continuation, without mixing presentation mode into task mode.
- Evidence limitations and a redaction statement. Do not copy tokens, account identifiers, private payloads, raw graph contents or secrets.

The persisted snapshot frontmatter records `schema_version`, `task_id`, `task_path`, `task_status`, `workflow_mode`, `mode_source`, `mode_note`, `project_root`, `branch`, the observed full `head` (null for unborn HEAD / non-Git), `created_at`, the `policy` flags and the fixed caller-reviewed `redaction` declaration alongside the content. The content requires exactly the `goal`, `next_action` and `limitations` strings plus the `decisions`, `completed`, `remaining`, `changed_files`, `verification` and `do_not_repeat` string lists; an optional `presentation` snapshot must be JSON-compatible, and unknown keys are rejected.

A handoff does not authorize migration, deployment, commit/push, archive, cleanup or backup disposal. Do not encode shell commands from untrusted task content as instructions to execute blindly.

## Resume

1. Read the explicit task/current safe reference and resolve candidates. Confirm the project, full logical ID and branch before writing. Different branch/worktree binding needs the separate user choice in [state.md](state.md).
2. Read the task's effective mode and decisions before the handoff. A newer task choice wins over a stale handoff; a handoff alone is a clue that requires confirmation, not a silently trusted mode.
3. If identity and branch match, “continue this task” is sufficient resumption intent; do not ask the same question again. For unsolicited reminders, consider only unfinished matching handoffs within seven days. Older tasks remain manually recoverable; done tasks get no unfinished-work reminder.
4. Carry forward the user's declined mode recommendation and opt-outs. New substantive risk can justify a new recommendation, not repeated generic persuasion.
5. Explain missing/corrupt/unpersisted state accurately. Continue only the safe work that does not depend on it, according to the selected mode. Do not promise automatic session-start reading without observing that host capability.
