---
title: "Start each authored file with a comment saying why it exists"
whenToRead: "Before creating, substantially changing, or reviewing a hand-written source, configuration, script, query, or documentation file, in any language or format."
impact: "LOW-MEDIUM"
impactDescription: "Without a header, readers and agents open and read a file to learn whether it is the one they need, and helpers that don't fit the file's purpose collect there unnoticed."
tags: "comments, documentation, file-headers"
---

## Start each authored file with a comment saying why it exists

Begin every hand-written file with a short comment that says why the file exists and what it is for, concretely enough that a reader can decide whether this is the file they need.
A label such as "helpers" or "component" doesn't say that.

### Implementation

- Keep the header to one to three lines, in the format's own comment syntax: `//` in Go and TypeScript, `--` in SQL, `#` in YAML and shell, `<!-- -->` in Markdown and HTML.
  Technology groups may set the exact form, such as where the header goes relative to a package clause.
- State the purpose, and what the file is not for when that would surprise a reader.
  Follow `comments-state-intent`: don't describe what other files or tools do with this one.
- Add a header to any file a change touches that lacks one.
- One file, one purpose: when a change adds something the header can't account for, put it in another file or rewrite the header.

Files that aren't written by hand, such as generated code, lockfiles, and vendored copies, need no header, because their generator or source owns them.
Neither do files whose format already states their identity and purpose, such as a rule file with a title and `whenToRead`, or a skill's `SKILL.md`.
A format with no comment syntax, such as JSON, needs no header.

### Examples

#### Application: A SQL query file

**Incorrect (counterexample):**

```sql
-- Queries.
-- name: ListActiveFolders :many
SELECT ...
```

"Queries" is true of every file in the directory.

**Correct:**

```sql
-- Reads and writes Brain folders, including their archive and Trash state.

-- name: ListActiveFolders :many
SELECT ...
```

### Validation

Check that each new or substantially changed hand-written file starts with a comment stating its purpose, and that the file's contents still fit that purpose.

A missing header on a generated, vendored, or self-describing file is not a violation.
