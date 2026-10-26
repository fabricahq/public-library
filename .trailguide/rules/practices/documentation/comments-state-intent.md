---
title: "Comment intent, and point at the owner instead of describing it"
whenToRead: "Before writing, changing, or reviewing a code or configuration comment, such as a file header, package or function documentation, or a comment about a tool, script, or check that uses the file."
impact: "MEDIUM"
impactDescription: "A comment that restates what code, a tool, or another file already says goes stale silently when that owner changes, and readers and agents then follow the stale text."
tags: "comments, documentation"
---

## Comment intent, and point at the owner instead of describing it

A comment carries what the code can't say: why this file or block exists, what it is for, and any constraint or contract a reader can't see in the code.
Don't describe what something does when authoritative code, a check, a rule, or a document already says it, whether that owner is the code right below the comment or another file or tool.
When a reader needs the owner, name it in one clause.

### Implementation

- State the purpose: "Exempt X from Y because Z", not "Tool T reads these marks to do U".
- Don't narrate the code below the comment, and don't describe how another file, script, tool, or service behaves.
- Don't describe call sites, consumers, or how another layer uses this code.
- Keep guidance on how to use a kind of file or package in the document that owns the convention, such as an architecture decision record or `AGENTS.md`, not in each instance's comment.
- A contract that the signature or types can't express, such as units, ordering, or failure modes, is intent the code doesn't state; keep it.
  Technology groups may say more about where such comments go.

### Rationale

A description of another owner's behavior is a second copy of a fact.
When the owner changes, nothing fails, so the copy stays wrong until someone notices, and an agent that reads the comment acts on the stale version.
Intent and constraints are the facts only this file can carry, so they stay true as long as the file keeps its purpose.

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

### Validation

For each new or changed comment, ask: if the code, file, tool, or check it mentions changed tomorrow while this file kept its purpose, would this comment become false?
If so, cut it to the intent and, when a reader needs it, a pointer to the owner.

A comment that names an owner without describing its behavior is not a violation, and neither is a comment stating a contract or constraint the code can't express.
