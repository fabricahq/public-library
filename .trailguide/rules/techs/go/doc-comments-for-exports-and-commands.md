---
title: "Give exported identifiers and commands doc comments"
whenToRead: "Before writing, changing, or reviewing an exported Go function, method, type, constant, or variable, a non-trivial unexported function, or a main package."
impact: "LOW-MEDIUM"
impactDescription: "Without doc comments, go doc and editors show callers nothing, so they read the implementation to learn the contract and may rely on details that aren't promised."
tags: "go, comments, godoc"
---

## Give exported identifiers and commands doc comments

Give every exported identifier a doc comment that starts with its name and states what callers can rely on.
Give each `main` package a doc comment saying what the command is for.
Comment an unexported function only when its intent or contract isn't clear from its name and signature.

### Implementation

- Start the comment with the identifier's name, as Go convention and `go doc` expect: `// ParseRange returns ...`.
- State the contract the signature doesn't show, such as units, ordering, whether it mutates its arguments, and when it returns an error.
  Follow `practices/documentation/comments-state-intent`: don't narrate the body or describe how callers use it.
- For a `main` package, attach the comment to `package main`, starting with `Command <name>` or a sentence about the program, and say what the command is for and when to run it.
  `comments-package-doc-vs-file-header` covers where package comments go.
- Unexported functions that parse, validate, format, synchronize, persist, or branch on subtle cases usually have a contract worth stating; short glue and one-line helpers usually don't.

### Examples

#### Application: An exported function

**Incorrect (counterexample):**

```go
// This function loops over the rows and builds a slice.
func ParseRows(data []byte) ([]Row, error) {
```

The comment narrates the body and says nothing callers can rely on.

**Correct:**

```go
// ParseRows decodes the ledger export into rows in file order.
// It returns an error naming the first line that has the wrong field count.
func ParseRows(data []byte) ([]Row, error) {
```

#### Application: A command

**Correct:**

```go
// Command seed loads sample orgs and Brain content into a local development
// database. Run it after a database reset.
package main
```

### Validation

Run `go doc` on changed packages and check that each exported identifier and each command has a doc comment stating its contract or purpose.
Linters such as `revive`'s `exported` rule can check that the comments exist; review judges whether they state a contract.

An unexported function without a comment is not a violation when its name and signature make its intent clear.
