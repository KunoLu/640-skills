---
name: lessons-record
description: Use when a durable lesson should be recorded after bug fixes, rollbacks, tool misjudgments, workflow errors, failed validation, GitNexus mismatch, or multi-agent context loss.
---

# Lessons Recording Skill

Use this Skill when durable lessons learned need to be recorded.

## Default Recording Structure

Trellis projects use the following layered lessons structure by default:

- `.trellis/spec/lessons.md`: A short required-reading entry point that stores only high-priority summaries, the reading protocol, and index guidance.
- `.trellis/lessons/index.md`: Maintains an index by `id`, tags, applicable scenarios, and detail paths.
- `.trellis/lessons/topics/<topic>.md`: Stores lesson details organized by topic.
- `.trellis/lessons/archive/YYYY-QN.md`: Stores infrequently accessed historical archives and is not read by default.

When recording a lesson, write it to `.trellis/lessons/topics/<topic>.md` and update `.trellis/lessons/index.md` by default; synchronize a summary to `.trellis/spec/lessons.md` only if it occurs frequently across tasks and its absence would repeatedly cause errors. Do not accumulate the complete lesson history in `.trellis/spec/lessons.md` over the long term.

Do not write to other locations unless the user explicitly specifies another path. Only when it has been confirmed that the project does not use Trellis should the default location be `docs/lessons.md`.

If the project does not use Trellis, but the project-level `AGENTS.md`, `docs/lessons.md`, or README explicitly adopts a layered lessons structure, follow the project structure instead of falling back to writing to a single file. A common non-Trellis layered structure is:

- `docs/lessons.md`: A short required-reading entry point that stores only the reading protocol, topic routing, and high-frequency summaries.
- `docs/lessons/index.md`: Maintains an index by `id`, tags, applicable scenarios, and detail paths.
- `docs/lessons/topics/<topic>.md`: Stores complete lesson details.
- `docs/lessons/archive/YYYY-QN.md`: Stores infrequently accessed historical archives and is not read by default.

Under this structure, when writing a new lesson, both the topic details and the index must be updated; only summaries of lessons that occur frequently across tasks should also be synchronized to `docs/lessons.md`.

---

## Lessons Split Name

Lessons files are tracked and every developer appends to them, so appended content must be scoped by a split name. Resolve that name before writing anything:

1. Read `name=` from `<repo-root>/.trellis/.developer`.
2. If that file is absent and the checkout is a linked git worktree, read `name=` from the main checkout's `.trellis/.developer`. `.developer` is gitignored by design, so a fresh `git worktree add` starts without one; read the main checkout's copy in place and do not copy it into the worktree.
3. Otherwise stop and ask the user for a split name. Do not proceed on a guess.

No other automatic source is permitted. Do not derive the name from `TRELLIS_DEVELOPER`, `git config user.name`, commit authors, or the directory names under `.trellis/workspace/`. A repository accumulates one `workspace/<name>/` directory for every developer who ever ran `trellis init`, and those directories are peers: none of them marks who is writing now.

The resolved name must be a single path-safe token: non-empty, and containing no `/`, `\`, or `..`. Report a value that violates this and stop; never silently rewrite it into a different name.

When no name can be resolved, list the existing directory names under `.trellis/workspace/` as candidates, point at `python3 ./.trellis/scripts/init_developer.py <name>` for establishing a local identity, and wait for the user.

Report the outcome with every lesson write:

```text
Lessons split name: <name>
Source: .developer | main-worktree | user-provided
```

## Marker Blocks

Append only inside the block owned by the resolved name:

```md
<!-- lessons:<name>:start -->
- content owned by <name>
<!-- lessons:<name>:end -->
```

Use these blocks in every file a lesson write touches: the short entry point, `index.md`, and each `topics/<topic>.md`.

- Write only inside your own block, and create it once. Later lessons extend the existing block instead of opening a new one.
- Never reorder, edit, or delete another name's block, including while resolving a merge conflict.
- Keep shared content, such as the reading protocol, above all blocks.
- Keep one blank line between adjacent blocks so concurrent appends stay separated by an unchanged line.

This removes the common conflict: when two developers append inside blocks that both already exist, their edits land in separate hunks with unchanged anchor lines between them and merge cleanly. One residual case remains. The first time two developers each create their own block in the same file, that conflicts once, because both insertions land at the same end-of-file position. Resolve it by keeping both blocks.

In `index.md`, give each name a complete table of its own inside its block rather than sharing one table:

```md
<!-- lessons:alice:start -->
| id | tags | read_when | summary | detail |
|---|---|---|---|---|
| LESSON-20260101-example | tag-a | When to read details | One-sentence summary | topics/workflow.md#lesson-20260101-example |
<!-- lessons:alice:end -->

<!-- lessons:bob:start -->
| id | tags | read_when | summary | detail |
|---|---|---|---|---|
| LESSON-20260102-example | tag-b | When to read details | One-sentence summary | topics/validation.md#lesson-20260102-example |
<!-- lessons:bob:end -->
```

Each block carries its own header row so that no marker ever lands between the rows of a single table, where an HTML comment would terminate the table.

A project that wants the residual first-creation conflict resolved automatically may opt into a union merge for append-only lessons paths in `.gitattributes`:

```text
.trellis/lessons/**/*.md merge=union
```

This is opt-in and not the default. A union merge keeps both sides of every concurrent change in that file, which suits append-only blocks but silently duplicates content when two developers genuinely edit the same shared line.

## Scenarios That Must Be Recorded

A lesson must be recorded when any of the following occurs:

- bug fixes
- rollbacks
- incorrect tool judgments
- mode-switching errors
- Trellis stage errors
- inappropriate parent / child task decomposition
- child tasks that cannot be independently validated
- task artifacts omitted during the check stage
- conflicts between task artifacts and `.trellis/spec`
- GitNexus impact analysis mismatches
- Channel / multi-Agent context loss
- recursive dispatch issues
- abnormal worker exits

---

## Recording Format

Use the following format for each lesson in a topic file:

```md
## LESSON-YYYYMMDD-<slug>: <short title>

- Date:
- Tags:
- Applicable scenarios:
- Severity:
- Source:
- Problem:
- Root cause:
- Fix:
- Prevention:
```

Use the following format for `index.md`:

```md
| id | tags | read_when | summary | detail |
|---|---|---|---|---|
| LESSON-YYYYMMDD-<slug> | tag-a, tag-b | When to read details | One-sentence summary | topics/<topic>.md#lesson-yyyymmdd-slug-short-title |
```

`.trellis/spec/lessons.md` stores only short summaries and the reading protocol, and should preferably remain within 150-200 lines. When it exceeds this range, first move infrequently accessed content into a topic or archive, then retain the index guidance.

## Writing Process

1. Determine whether it truly qualifies as a durable lesson; do not record ordinary task summaries, one-off implementation details, or temporary research.
2. Resolve the lessons split name and report it. Stop and ask the user if it cannot be resolved.
3. Select a topic, such as `workflow`, `validation`, `shell`, `markdown`, `gitnexus`, `trellis-channel`, `ui`, or a project domain name.
4. Append the complete lesson to `.trellis/lessons/topics/<topic>.md`, inside your own marker block.
5. Add or update an index row inside your own marker block in `.trellis/lessons/index.md`, ensuring that the tags, `read_when`, and detail path are searchable.
6. Only when the lesson represents a frequently occurring risk across tasks should a one-sentence prevention rule be synchronized to `.trellis/spec/lessons.md`, inside your own marker block.
7. When a topic file becomes too long or its content is infrequently accessed, retain the summary and index, and move the old details into your own marker block in `.trellis/lessons/archive/YYYY-QN.md`.

## Reading Boundaries

- Marker blocks scope writes, not reads. When a file is read, read every name's blocks, not only your own.
- When starting ordinary Trellis work, read only `.trellis/spec/lessons.md` by default.
- Do not read all of `.trellis/lessons/**` by default.
- Read the corresponding topic or archive only after a match is found based on the current task, error message, tool name, language, tags, or `read_when`.
- Do not read `archive/` by default; read it only for recurring issues, failed troubleshooting, user-requested traceability, or when the index explicitly points to it.