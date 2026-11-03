---
title: "Comment intent, and point at the owner instead of describing it"
whenToRead: "Before writing, changing, or reviewing a code or configuration comment, such as a file header, package or function documentation, or a comment about a tool, script, or check that uses the file."
impact: "MEDIUM"
impactDescription: "A comment that restates what code, a tool, or another file already says goes stale silently when that owner changes, and readers and agents then follow the stale text."
tags: "comments, documentation"
---

## Comment intent, and point at the owner instead of describing it

Document purpose, observable contracts, and constraints where readers need them: why this file or block exists, what callers can rely on, and any constraint a reader can't see in the code.
Don't duplicate implementation details or conventions that an authoritative owner already states, whether that owner is the code right below the comment or another file, tool, or document.
When a reader needs the owner, name it in one clause.

### Implementation

- Before writing a comment inside a function body, or one explaining why our own code is surprising, try to make it unnecessary with a clearer name, a narrower type, a test, or a lint rule.
  Comment only what remains.
  Doc comments on exported interfaces and definitions of domain fields are written even when the code is clear.
- State the purpose: "Exempt X from Y because Z", not "Tool T reads these marks to do U".
- Don't narrate the steps of the code below the comment.
- Don't retell how another file, script, or tool works, or list the call sites and consumers of this code: they change without this file changing.
- Keep guidance on how to use a kind of file or package in the document that owns the convention, such as an architecture decision record or `AGENTS.md`, not in each instance's comment.
- Keep a contract that callers rely on and the signature or types can't express, such as units, ordering, failure modes, or what a public function guarantees.
- Keep the outside constraint that explains local code, such as a vendor limit, browser behavior, protocol requirement, or legal requirement.
  Say only the part that causes the constraint, and link the upstream source when there is one.
  When you don't know the reason for a value, don't guess one.
- Delete commented-out code instead of keeping it; version control keeps the old version.
- Don't use banner comments, such as a row of `=` or `// ---- Helpers ----`, to divide a file into sections; split the file or let the declarations speak.

### Rationale

A description of another owner's behavior is a second copy of a fact.
When the owner changes, nothing fails, so the copy stays wrong until someone notices, and an agent that reads the comment acts on the stale version.
Intent, contracts, and the reasons for constraints are the facts only this file can carry, so they stay true as long as the file keeps its purpose.
Without them, a reader has to trace the implementation to learn what it promises, and a constraint whose cause isn't stated looks arbitrary enough to remove.

### Examples

#### Application: A configuration file used by a tool

**Incorrect (counterexample):**

```gitattributes
# The ratchet script runs `git check-attr linguist-generated` on each staged
# file and skips any file marked here. GitHub also collapses these files in
# pull request diffs.
gen/** linguist-generated
```

The comment describes the ratchet script and GitHub.
It becomes false when either one changes how it reads the attribute.

**Correct:**

```gitattributes
# Exempt the files nobody edits by hand from the source size budget:
# generated outputs and vendored sources.
gen/** linguist-generated
```

The comment says why the files are marked and leaves the tools' behavior to the tools.

#### Application: A package that follows a shared convention

**Incorrect (counterexample):**

```go
// Package shared holds the IDs and enums that other contexts import. Other
// contexts may import it from any layer, but it must not import the rest of
// this context. Call sites in billing and search use it for ArtifactType.
package shared
```

The comment restates the convention and lists consumers.
Both change without this file changing.

**Correct:**

```go
// Package shared holds the terms Brain shares with other bounded contexts.
// ADR 0002 ("Cross-context rules") says what belongs here and how other
// contexts import it.
package shared
```

The comment states the package's purpose and names the owner of the convention without retelling it.

#### Application: A public function's contract

**Incorrect (counterexample):**

```go
// Reserve locks the SKU's row with SELECT ... FOR UPDATE, decrements its
// count, and commits.
func (s *Store) Reserve(ctx context.Context, sku string, n int) error
```

The comment narrates the implementation, and leaves out what a caller needs: whether a partial reservation can happen and what a shortage returns.

**Correct:**

```go
// Reserve holds n units of sku. It reserves all n or none, and returns
// ErrInsufficientStock when fewer than n are available.
func (s *Store) Reserve(ctx context.Context, sku string, n int) error
```

Keep this comment: the all-or-none guarantee and the error are a contract the signature can't express.

#### Application: A constraint from another service

**Incorrect (counterexample):**

```ts
// Wait before refunding.
await sleep(1_100);
```

Cutting the reason leaves a delay that looks arbitrary, and the next reader may remove it.

**Correct:**

```ts
// The payment provider rejects a refund issued within one second of its
// charge.
await sleep(1_100);
```

Keep this comment: it describes another service, but only the behavior that sets this delay.

### Validation

For each new or changed comment, ask: if the code, file, tool, or check it mentions changed tomorrow while this file kept its purpose, would this comment become false?
If so, and the comment retells an implementation or a convention someone else owns, cut it to the intent and, when a reader needs it, a pointer to the owner.

A comment that names an owner without describing its behavior is not a violation.
Neither is a comment stating a contract the code can't express, or the outside behavior that causes a local constraint: if that behavior changed, the constraint would change with it.
Before removing a comment, check that it isn't one of these.

Commented-out code and banner comments are always violations; Go's `gocritic` `commentedOutCode` check finds the first.
