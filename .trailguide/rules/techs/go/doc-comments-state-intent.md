---
title: "Give exported Go identifiers and non-obvious functions doc comments stating their intent"
whenToRead: "Before writing, changing, or reviewing a Go function or method, exported or not, an exported type, constant, or variable, or a main package."
impact: "LOW-MEDIUM"
impactDescription: "Without an intent comment, readers and agents read a function's body to learn what it is for, and callers rely on details nobody promised."
tags: "go, comments, godoc"
---

## Give exported Go identifiers and non-obvious functions doc comments stating their intent

A doc comment carries what a reader needs that the name, types, and code don't already say.
Give every exported identifier a doc comment that starts with its name and states its intent: what it accomplishes for its caller, not how.
Add what callers can rely on beyond the name and signature, such as units, ordering, mutation, cancellation, atomicity, or failure modes, and document every guarantee callers depend on, however many sentences that takes.
Give an unexported function the same kind of comment when its intent or constraints aren't apparent from its name and signature.
Give each `main` package a doc comment saying what the command is for.

### Implementation

- Start the comment with the identifier's name, as Go convention and `go doc` expect: `// parseRange turns ...`.
- A comment that only restates the name adds nothing: say what the function does for its caller that the name doesn't.
  When an unexported function has nothing to add, such as `isEmpty`, leave it uncommented rather than write filler.
- When the intent or contract takes more than a few sentences, treat that as a signal to reconsider the interface, not as a limit: a cohesive operation can have several guarantees worth stating in full.
- Don't narrate the body or describe how callers use it.
- For a `main` package, write the comment as `// Command <name> ...` or a sentence about the program, saying what it is for and when to run it.
  Attach it directly above `package main` with no blank line, or `go doc` won't show it.

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

#### Application: An unexported function

**Incorrect (counterexample):**

```go
// parseRow parses a row.
func parseRow(line string) (Row, error) {
```

The comment repeats the name, so it tells the reader nothing.

**Correct:**

```go
// parseRow turns one line of the ledger export into a row with its amount in cents.
func parseRow(line string) (Row, error) {
```

The sentence says what the caller gets that the name doesn't: a row, from one export line, with the amount converted.

A helper like `func isBlank(s string) bool { return strings.TrimSpace(s) == "" }` needs no comment: its name and one-line body already say everything.

#### Application: A command

**Correct:**

```go
// Command seed loads sample orgs and Brain content into a local development
// database. Run it after a database reset.
package main
```

### Validation

Run `go doc` on changed packages and check that each exported identifier and command has a doc comment.
`revive`'s `exported` and `package-comments` rules check presence and form for exported identifiers.
Review judges whether each comment states intent rather than restating the name, and whether an uncommented unexported function's intent and constraints really are apparent.

An unexported function without a comment is not a violation when its name and signature say everything a reader needs.
