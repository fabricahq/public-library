---
title: "Give exported TypeScript interfaces and non-obvious functions doc comments stating their intent"
whenToRead: "Before planning, writing, changing, or reviewing a TypeScript function, method, class, or component, exported or not, an exported type, a TypeScript file header, or the lint configuration that checks doc comments."
impact: "MEDIUM"
impactDescription: "Missing or filler doc comments force readers and agents to trace implementations to learn what a function is for and what callers can rely on."
tags: "typescript, comments, tsdoc, documentation"
attribution:
  - url: https://github.com/mkosir/typescript-style-guide/blob/86bebd58a987e23277dba02028c0ee2d6ffb5073/website/src/pages/index.mdx
    description: "Adapted from mkosir TypeScript Style Guide guidance (comment-role-result-and-constraints; MIT, notice retained in NOTICE.md): restructured to the rule template, extended with contract-first design, and narrowed to TSDoc form and tooling for function intent and file headers."
---

## Give exported TypeScript interfaces and non-obvious functions doc comments stating their intent

A doc comment carries what a reader needs that the name, types, and code don't already say.
Give every exported function, class, method, type, and component a TSDoc comment that states its intent: what it accomplishes for its caller, not how.
Add what callers can rely on beyond the name and signature, such as ordering, case, locale, units, mutation, empty input, cancellation, atomicity, and failure modes, and document every guarantee callers depend on.
Give an unexported function or method the same kind of comment when its intent or constraints aren't apparent from its name and signature.
Inline callbacks, such as the function passed to `map` or an event handler written in place, need none.

### Implementation

- **Intent, not filler:** a comment that restates the name fails, such as `/** Parses rows. */` on `parseRows`.
  Say what the caller gets that the name doesn't.
  When an unexported function has nothing to add, such as `isEmpty`, leave it uncommented rather than write filler.
- **Length as a signal:** when the intent or contract takes more than a few sentences, reconsider the interface, but document a cohesive operation's guarantees in full rather than cut them.
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
A helper like `const isBlank = (s: string) => s.trim() === '';` needs no comment: its name and body already say everything.

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

Check that each exported function, class, method, type, and component has a doc comment stating its intent, and that it states the contract its signature doesn't show.
For a new or materially changed interface, inspect its drafted contract and confirm the finished behavior matches it.

Lint the exported scope with `eslint-plugin-jsdoc`.
`require-jsdoc` checks only function declarations by default, so list the other forms explicitly:

```js
'jsdoc/require-jsdoc': ['error', {
  publicOnly: true,
  require: {
    FunctionDeclaration: true,
    FunctionExpression: true,
    ArrowFunctionExpression: true,
    ClassDeclaration: true,
    MethodDefinition: true,
  },
  contexts: ['TSInterfaceDeclaration', 'TSTypeAliasDeclaration'],
}],
'jsdoc/require-description': 'error',
'jsdoc/informative-docs': 'error',
'jsdoc/require-param': 'off',
'jsdoc/require-returns': 'off',
```

With this configuration, `export function f() {}`, `export const f = () => {}`, an exported class and its public methods, and exported types and interfaces fail without a doc comment.
Unexported functions, `private` methods, and inline callbacks pass without one, because whether their intent is apparent is a judgment for review.
`informative-docs` fails a description made only of the name's words, such as `/** Parse rows. */` on `parseRows`, but passes `/** Parses rows. */`, so review still judges whether each comment states intent rather than restating the name.
`require-file-overview` recognizes only the `@file` block form, so a project that checks `//` headers needs its own check.

An unexported function without a comment is not a violation when its name and signature say everything a reader needs.
