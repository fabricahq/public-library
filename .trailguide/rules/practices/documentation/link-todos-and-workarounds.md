---
title: "Link every TODO and workaround to where it will be resolved"
whenToRead: "Before writing, changing, or reviewing a TODO, FIXME, or a workaround for a bug or limitation in a dependency, platform, or another team's code."
impact: "LOW-MEDIUM"
impactDescription: "A TODO or workaround without a link has no owner and no exit condition, so it stays long after its cause is fixed and nobody knows whether it's safe to remove."
tags: "comments, todos, workarounds"
---

## Link every TODO and workaround to where it will be resolved

Every TODO, FIXME, and workaround comment links the issue, pull request, or upstream document that tracks it.

### Implementation

- Link the tracker entry, not a person: `// TODO(https://github.com/org/repo/issues/123): ...`, not `// TODO(alice): ...`.
- For a workaround, link the upstream bug or documentation that explains the limitation, so a reader can check whether it still applies.
- If no issue exists yet, open one before merging the comment.

### Examples

**Incorrect (counterexample):**

```go
// TODO: handle pagination
```

Nothing says who tracks it or when it matters.

**Correct:**

```go
// TODO(https://github.com/fabricahq/greenfield/issues/412): page through results once orgs exceed 1,000 folders.
```

### Validation

Search changed files for `TODO`, `FIXME`, and workaround comments, and check that each has a link to an issue, pull request, or upstream document.
