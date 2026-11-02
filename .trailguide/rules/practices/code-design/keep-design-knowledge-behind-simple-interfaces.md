---
title: "Keep design knowledge behind simple interfaces"
whenToRead: "Before planning, writing, changing, or reviewing module boundaries and APIs, such as deciding who owns a format, invariant, lifecycle, or sequence of operations."
impact: "HIGH"
impactDescription: "Design decisions spread across callers cause coordinated edits, duplicated invariants, and failures when callers miss an implementation requirement."
tags: "code-design, information-hiding, interfaces, ownership"
attribution:
  - url: https://web.stanford.edu/~ouster/cgi-bin/book.php
    description: "Original guidance informed by chapters 4-9 of John Ousterhout's A Philosophy of Software Design, second edition; examples and wording are original."
---

## Keep design knowledge behind simple interfaces

Give each implementation decision one owner, and expose operations that callers can use from their contracts without learning that owner's implementation.
Judge a boundary by the knowledge it hides and the work it saves callers.

### Implementation

- Identify the knowledge the module owns, such as a storage format, validation invariant, resource lifecycle, or algorithm.
  Keep the code that must agree on that knowledge together behind its interface.
- Include informal requirements when evaluating an interface: required call order, ownership, failure behavior, and configuration choices count just as much as parameters and return types.
- Offer complete operations for current needs.
  Keep implementation sequencing and intermediate representations inside the owner when callers have no independent use for them.
  Expose domain policy or information that only the caller can supply.
- Prefer a small set of operations that covers current uses over a method for each caller's special case.
  A general interface can be useful with one consumer; it does not require speculative features or moving the code into a shared folder.
- Keep a layer when it hides a meaningful decision or presents a different abstraction.
  A wrapper that only renames another operation adds navigation without hiding knowledge.
- Preserve separate modules when they own independent concepts.
  Sharing a few values is not sufficient reason to merge them; identify the decision that would otherwise require coordinated changes.

### Rationale

A module is deep when its simple interface hides substantial implementation knowledge.
Putting fields behind private access does not achieve this if callers still have to know their representation or coordinate their updates.
Feature folders help locate code, but the module boundary determines which design decisions callers depend on.

### Examples

These examples describe interfaces; their language and storage medium are illustrative.

#### Application: Reading and writing one format

**Incorrect (counterexample):**

A settings reader and writer each maintain their own definitions of field names, defaults, and escaping rules.
Changing the format requires finding and changing both definitions, even though both classes keep their fields private.

**Correct:**

A settings codec owns those decisions and exposes `decode(text)` and `encode(settings)` with documented results and failures.
The storage code can still own disk access, but it no longer interprets fields in the format.
Changing escaping rules affects the codec without changing its callers.

#### Application: Callers assembling a complete operation

**Incorrect (counterexample):**

Every caller that saves a document must serialize it, write a temporary file, and rename that file in the correct order.
Callers pass the temporary path between operations solely to finish the save.

**Correct:**

The persistence module exposes `saveDocument(path, document)` and owns serialization and temporary-file handling.
Its contract states the replacement and failure guarantees it actually provides; the method name alone does not promise atomicity or crash durability.
The caller chooses the document and destination, while the module owns the save mechanism.

#### Application: Independent capabilities

**Correct:**

A pure document formatter and a file writer remain separate when callers also use the formatted output in previews or send it over a network.
A save operation may compose them internally.
Their independent uses justify the separation; using both during a save is not itself a violation.

### Validation

Name the implementation decision hidden by each new or changed boundary.
Walk a common caller using only the contract: identify any extra format knowledge, ordering rule, or intermediate state it must manage.
Then trace a plausible change to the hidden decision and check that callers can remain unchanged while the contract holds.

A small module, a single consumer, or code organized into several files is not by itself evidence of a violation.
Point to leaked knowledge or unnecessary caller work before proposing a structural change.
