---
title: "Give every Go function a doc comment stating its intent"
whenToRead: "Before writing, changing, or reviewing a Go function or method, exported or not, an exported type, constant, or variable, or a main package."
impact: "LOW-MEDIUM"
impactDescription: "Without an intent comment, readers and agents read a function's body to learn what it is for, and callers rely on details nobody promised."
tags: "go, comments, godoc"
---

## Give every Go function a doc comment stating its intent

Give every function, exported or not, a one-sentence doc comment that starts with its name and states its intent: what it accomplishes for its caller, not how.
For exported identifiers, add only what callers can rely on beyond the name and signature, such as units, ordering, mutation, or failure modes.
If the intent or contract needs more than a few sentences, simplify the function or API.
Give each `main` package a doc comment saying what the command is for.

### Implementation

- Start the comment with the identifier's name, as Go convention and `go doc` expect: `// parseRange turns ...`.
- A comment that only restates the name adds nothing: say what the function does for its caller that the name doesn't.
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

#### Application: A command

**Correct:**

```go
// Command seed loads sample orgs and Brain content into a local development
// database. Run it after a database reset.
package main
```

### Validation

Run `go doc` on changed packages and check that each function, exported identifier, and command has a doc comment.
`revive`'s `exported` and `package-comments` rules check presence and form for exported identifiers.
Unexported functions rely on review or a custom check.
Review judges whether each comment states intent rather than restating the name.
