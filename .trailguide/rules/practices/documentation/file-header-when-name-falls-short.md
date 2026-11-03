---
title: "Head a file with its purpose only when its name can't say it"
whenToRead: "Before creating, renaming, substantially changing, or reviewing a hand-written source, configuration, script, query, or documentation file, in any language or format."
impact: "LOW"
impactDescription: "A file whose name doesn't say what it is for makes readers and agents open it to find out, and a header that repeats the name is one more comment to keep true."
tags: "comments, documentation, file-headers"
---

## Head a file with its purpose only when its name can't say it

Start a hand-written file with a one-to-three-line comment only when its name and location don't tell a reader whether it's the file they need, or when it deliberately excludes something a reader would expect there.
Prefer a more specific file name to a header.
A label such as "helpers" or "component" says neither.

### Implementation

- Write the header in the format's own comment syntax: `//` in Go and TypeScript, `--` in SQL, `#` in YAML and shell, `<!-- -->` in Markdown and HTML.
- State what the file is not for when that would surprise a reader.
- State what the file is for, not what other files or tools do with it.
- One file, one purpose: when a change adds something the header can't account for, put it in another file or rewrite the header.

Files that aren't written by hand, such as generated code, lockfiles, and vendored copies, need no header, because their generator or source owns them.
Neither do files whose format already states their identity and purpose, such as a rule file with a title and `whenToRead`, or a skill's `SKILL.md`.
A format with no comment syntax, such as JSON, needs no header.

### Examples

#### Application: A SQL query file with a generic name

**Incorrect (counterexample):** `queries.sql`

```sql
-- Queries.
-- name: ListActiveFolders :many
SELECT ...
```

Neither the name nor the header says which queries live here.

**Correct:** `folders.sql`

```sql
-- name: ListActiveFolders :many
SELECT ...
```

The file is renamed for what it holds, so it needs no header.

#### Application: A file that leaves out something a reader would expect

**Correct:** `ledger-csv.ts`

```ts
// Not a general CSV parser: the ledger export never quotes fields or embeds commas.
```

The name says what the file is for; the header states what it deliberately doesn't handle.

### Validation

Check that each header states something the file's name and location don't, and that the file's contents still fit it.
A file with no header isn't a violation when its name says what it's for.
