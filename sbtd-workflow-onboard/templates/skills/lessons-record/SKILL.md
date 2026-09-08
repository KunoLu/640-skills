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

The resolved name must match `^[a-z0-9]+$`: non-empty, lowercase letters and digits only, with no separators of any kind. This is stricter than path safety, which it also satisfies. Report a name that violates it, saying what was read and why it was rejected, and ask the user for a conforming split name. Never rewrite a non-conforming name into a conforming one.

Rewriting is what would break uniqueness. Lowercasing `Alice` and folding `a_b` each map two distinct developers onto one ID segment, so on the same day with the same slug the two would emit a byte-identical lesson ID, which is the collision the ID is meant to prevent. Excluding `-` from the name serves the same end: it holds the name to exactly one `-`-delimited field of the ID, so a name and a slug cannot trade characters across their boundary and reach one ID from two different pairs.

A `.developer` file that was found but holds a non-conforming `name=`, such as `Alice`, `alice.wang`, `zhang_san`, or a CJK name, does not yield a split name; stop and ask as above. Point at `python3 ./.trellis/scripts/init_developer.py <name>` for aligning `.developer` with a conforming name so later writes resolve without asking.

When no name can be resolved, list the conforming directory names under `.trellis/workspace/` as candidates, point at `python3 ./.trellis/scripts/init_developer.py <name>` for establishing a local identity, and wait for the user.

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
| LESSON-20260101-alice-example | tag-a | When to read details | One-sentence summary | topics/workflow.md#lesson-20260101-alice-example |
<!-- lessons:alice:end -->

<!-- lessons:bob:start -->
| id | tags | read_when | summary | detail |
|---|---|---|---|---|
| LESSON-20260102-bob-example | tag-b | When to read details | One-sentence summary | topics/validation.md#lesson-20260102-bob-example |
<!-- lessons:bob:end -->
```

Each block carries its own header row so that no marker ever lands between the rows of a single table, where an HTML comment would terminate the table.

A project that wants the residual first-creation conflict resolved automatically may opt into a union merge for append-only lessons paths in `.gitattributes`:

```text
.trellis/lessons/**/*.md merge=union
```

This is opt-in and not the default. A union merge keeps both sides of every concurrent change in that file, which suits append-only blocks but silently duplicates content when two developers genuinely edit the same shared line.

That pattern covers the index, topic, and archive files only. It deliberately excludes `.trellis/spec/lessons.md`, which also carries marker blocks but is not append-only: summaries there get rewritten and pruned back under the line budget, and a union merge would silently duplicate them. A first-creation conflict in that file stays manual.

## Lesson IDs

Marker blocks isolate writes, not the ID namespace. Two developers can reach for the same date and the same slug on the same day, and nothing in the block protocol stops them: the two `## LESSON-...` headings land in one topic file as byte-identical text, and both index rows carry a byte-identical `detail` value. The index can then no longer say which lesson a link points at. Put the split name in the ID so that two developers writing on the same day about the same subject no longer collide:

```text
LESSON-YYYYMMDD-<name>-<slug>
```

- `<name>` is the resolved split name verbatim. It is already `[a-z0-9]+`, so there is nothing to transform, and no transformation is permitted: the marker block and the ID must carry the same characters. A rule that folded the name into the ID would hand two distinct names one ID segment and reinstate the collision.
- `<slug>` is lowercase and may contain `-`; `<name>` may not. That is what keeps the ID unambiguous. `<name>` is the single field between the date and the first `-` of the slug, so one date, name and slug yield one ID, and no other name and slug pair yields that same ID.
- Nothing parses the ID back into its parts. Ownership comes from the enclosing marker block; the name is in the ID for uniqueness and readability.
- Do not rename a lesson ID that already exists. Renaming rewrites the heading, which breaks every `detail` anchor and cross-reference already pointing at it. This rule applies to newly recorded lessons.
- The name separates new IDs from each other, not from every ID already recorded. Retained legacy IDs share this namespace, and a legacy ID shaped `LESSON-YYYYMMDD-<word>-<rest>` is indistinguishable from a new ID whose name is `<word>`. Before writing, search the lessons tree for the exact ID and its derived anchor; if either already exists, choose a different slug. Uniqueness rests on that check, not on the format alone.

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
## LESSON-YYYYMMDD-<name>-<slug>: <short title>

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
| LESSON-YYYYMMDD-<name>-<slug> | tag-a, tag-b | When to read details | One-sentence summary | topics/<topic>.md#lesson-yyyymmdd-name-slug-short-title |
```

`.trellis/spec/lessons.md` stores only short summaries and the reading protocol, and should preferably remain within 150-200 lines. When it exceeds this range, first move infrequently accessed content into a topic or archive, then retain the index guidance.

## Writing Process

1. Determine whether it truly qualifies as a durable lesson; do not record ordinary task summaries, one-off implementation details, or temporary research.
2. Resolve the lessons split name and report it. Stop and ask the user if it cannot be resolved.
3. Select a topic, such as `workflow`, `validation`, `shell`, `markdown`, `gitnexus`, `trellis-channel`, `ui`, or a project domain name.
4. Append the complete lesson to `.trellis/lessons/topics/<topic>.md`, inside your own marker block, under a `LESSON-YYYYMMDD-<name>-<slug>` ID.
5. Add or update an index row inside your own marker block in `.trellis/lessons/index.md`, ensuring that the tags, `read_when`, and detail path are searchable.
6. Only when the lesson represents a frequently occurring risk across tasks should a one-sentence prevention rule be synchronized to `.trellis/spec/lessons.md`, inside your own marker block.
7. When a topic file becomes too long or its content is infrequently accessed, retain the summary and index, and move the old details into your own marker block in `.trellis/lessons/archive/YYYY-QN.md`.

## Reading Boundaries

- Marker blocks scope writes, not reads. When a file is read, read every name's blocks, not only your own.
- When starting ordinary Trellis work, read only `.trellis/spec/lessons.md` by default.
- Do not read all of `.trellis/lessons/**` by default.
- Read the corresponding topic or archive only after a match is found based on the current task, error message, tool name, language, tags, or `read_when`.
- Do not read `archive/` by default; read it only for recurring issues, failed troubleshooting, user-requested traceability, or when the index explicitly points to it.