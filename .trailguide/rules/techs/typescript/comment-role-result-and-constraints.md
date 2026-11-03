---
title: "Give every TypeScript function a doc comment stating its intent"
whenToRead: "Before planning, writing, changing, or reviewing a TypeScript function, method, or component, exported or not, an exported type, or a TypeScript file header."
impact: "MEDIUM"
impactDescription: "Missing or filler doc comments force readers and agents to trace implementations to learn what a function is for and what callers can rely on."
tags: "typescript, comments, tsdoc, documentation"
attribution:
  - url: https://github.com/mkosir/typescript-style-guide/blob/86bebd58a987e23277dba02028c0ee2d6ffb5073/website/src/pages/index.mdx
    description: "Adapted from mkosir TypeScript Style Guide guidance (comment-role-result-and-constraints; MIT, notice retained in NOTICE.md): restructured to the rule template, extended with contract-first design, and narrowed to TSDoc form and tooling for function intent and file headers."
---

## Give every TypeScript function a doc comment stating its intent

Give every function, method, and component, exported or not, a one-sentence TSDoc comment stating its intent: what it accomplishes for its caller, not how.
For exported functions, types, and components, add only what callers can rely on beyond the name and signature, such as ordering, case, locale, units, mutation, empty input, and failure modes.
If the intent or contract needs more than a few sentences, simplify the function or API.

### Implementation

- **Intent, not filler:** a comment that restates the name fails, such as `/** Parses rows. */` on `parseRows`.
  Say what the caller gets that the name doesn't.
- **Form:** write doc comments as `/** ... */` directly above the declaration.
  Drop `@param` and `@returns` tags that repeat names and types; keep `@throws` only when it names the condition.
- **Contract first:** draft the contract of a new or materially changed exported interface before its implementation.
  When a complete contract is difficult to explain simply, reconsider the interface rather than omitting its constraints.
  Check the draft against the finished code and tests; a drafted promise is not evidence it is implemented.
- **File headers:** when a file needs a header, write it as a `/** @fileoverview ... */` block or `//` lines at the top of the file.
  A bare `/** */` before the first declaration documents that declaration instead.

### Rationale

An intent comment tells a reader what a function is for without reading its body, and an export comment tells a caller what they get.
Agent-written code tends to fail this by omission, or with comments and `@param` tags that repeat the signature.

### Examples

#### Application: An exported function

**Incorrect (counterexample):**

```ts
/**
 * Parses transactions.
 * @param csv - The CSV string to parse
 * @returns The parsed transactions
 */
export function parseTransactions(csv: string): Array<Transaction> {
  return splitRows(csv).map(parseRow);
}
```

The comment repeats the name and signature.

**Correct:**

```ts
/**
 * Parse the ledger export into transactions with amounts in integer cents.
 * Tolerates a leading UTF-8 BOM, CRLF line endings, and blank lines.
 * Throws on a row with the wrong field count, an unparsable timestamp,
 * or an amount that is not a two-decimal number.
 */
export function parseTransactions(csv: string): Array<Transaction> {
  return splitRows(csv).map(parseRow);
}
```

These contract details must be verified against `splitRows` and `parseRow`, not inferred from the function's name.

#### Application: An unexported function

**Incorrect (counterexample):**

```ts
/** Parses a row. */
function parseRow(line: string): Transaction {
```

**Correct:**

```ts
/** Turn one line of the ledger export into a transaction with its amount in cents. */
function parseRow(line: string): Transaction {
```

The sentence says what the caller gets that the name doesn't.

#### Application: An observable result

**Incorrect (counterexample):**

```ts
/** Sorts folders by name. */
export function sortFolders(folders: ReadonlyArray<Folder>): Array<Folder> {
  return [...folders].sort((a, b) => a.name.localeCompare(b.name, 'en-US', { sensitivity: 'base' }));
}
```

**Correct:**

```ts
/** Return a new array ordered by name using en-US collation, ignoring case and accents. */
export function sortFolders(folders: ReadonlyArray<Folder>): Array<Folder> {
  return [...folders].sort((a, b) => a.name.localeCompare(b.name, 'en-US', { sensitivity: 'base' }));
}
```

### Validation

Check that each function has a doc comment stating its intent, and that each export's comment states the contract its signature doesn't show.
For a new or materially changed interface, inspect its drafted contract and confirm the finished behavior matches it.
Lint for presence and filler with `eslint-plugin-jsdoc`: enable `require-jsdoc` with `publicOnly: false`, `require-description`, and `informative-docs`, and disable `require-param` and `require-returns`.
`require-file-overview` recognizes only the `@file` block form, so a project that checks `//` headers needs its own check.
Review judges whether each comment states intent rather than restating the name.
