---
title: "Give every lint or type-checker suppression a reason"
whenToRead: "Before adding, changing, or reviewing a comment that disables a linter or type-checker check, such as `//nolint`, `// eslint-disable-next-line`, `@ts-expect-error`, `# noqa`, or `# type: ignore`."
impact: "MEDIUM"
impactDescription: "A suppression without a reason can't be judged or safely removed, so it outlives the problem it hid and masks new ones."
tags: "comments, linting, type-checking, suppressions"
---

## Give every lint or type-checker suppression a reason

Every comment that disables a lint or type-checker check names the specific check it disables and says why the code is right despite it.

### Implementation

- Name the one check, not a whole category: `//nolint:errcheck`, not `//nolint`.
- Put the reason on the same comment, in a sentence a reviewer can verify, such as the upstream bug or the invariant that makes the code safe.
- Suppress the narrowest scope: one line rather than a block, and a block rather than a file.
- Enforce it with the tool where you can: Go's `nolintlint` with `require-explanation` and `require-specific`, typescript-eslint's `ban-ts-comment` with `allow-with-description`, and `eslint-comments/require-description`.

### Examples

#### Application: A Go linter suppression

**Incorrect (counterexample):**

```go
defer f.Close() //nolint
```

The comment disables every linter on the line and gives no reason.

**Correct:**

```go
defer f.Close() //nolint:errcheck // Read-only file; a close error can't lose data.
```

#### Application: A TypeScript type error

**Incorrect (counterexample):**

```ts
// @ts-expect-error
chart.render(options);
```

**Correct:**

```ts
// @ts-expect-error The chart library's types omit `animate`; fixed upstream in v5 (https://github.com/example/chart/issues/412).
chart.render(options);
```

### Validation

Search changed files for suppression comments and check that each names one check and gives a reason a reviewer can verify.
