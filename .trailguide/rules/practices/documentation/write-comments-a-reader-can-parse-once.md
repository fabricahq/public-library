---
title: "Write comments in plain sentences a reader can parse once"
whenToRead: "Before writing, changing, or reviewing a code or configuration comment, such as a file header, package, type, function, or field documentation, or a comment inside a function body."
impact: "MEDIUM"
impactDescription: "A comment that readers must parse twice slows every later change to its code, and one they misread leads people and agents to change the code wrongly."
tags: "comments, documentation, writing"
---

## Write comments in plain sentences a reader can parse once

Write each comment so a maintainer understands it on the first read.
Give each sentence a subject the reader can find in the code or the world, put its verb right after it, and keep the object close to the verb.
State one fact or reason per sentence, in words the file's readers already know.

### Implementation

- Say what acts.
  Name the type, function, caller, or service ("reportingHandler sends", "The provider rejects"), not a bare verb with no subject ("Sends every record").
  Where the language has a doc-comment convention, such as Go's starting with the identifier, follow it.
- Keep the subject, verb, and object together.
  Don't wedge a long phrase between them, as in "hands records, with the attrs and groups the logger accumulated, to reporter."
  Move the phrase into its own sentence.
- Don't stack clauses or nouns inside one phrase, as in "every error-level record a process logs" or "the groups open when they were added."
  Add "that" or "which," or split the sentence.
- Give a chain of reasoning one step per sentence.
  A sentence that carries a premise, a consequence, and a benefit joined by "so" and "without" is three sentences.
- Use the code's own names for code, and plain words for everything else.
  Don't coin a verb or reuse a word in a private sense, such as "tee" or "qualified."
  When the reader needs a technical term they may not know, explain it in a clause.
- State what the code does rather than what it avoids.
  "Code that logs an error doesn't also need to report it" is clearer than "without a second call that a new error site could forget."

### Exceptions

- A short annotation can be a phrase, such as a field's unit (`// in seconds`) or a value's meaning (`// per attempt, not total`).
- Leave formats that a tool or law prescribes as they are, such as license headers, build tags, generated-code markers, and lint directives.
- Quote an error message, protocol text, or upstream comment exactly.
- Terms that every reader of this codebase knows, such as its domain vocabulary or the language's standard terms, need no explanation.

### Rationale

People read a comment in the middle of a task, to confirm what code promises before they change it.
Agents read it the same way, and act on what they take it to mean.
A compressed sentence saves the writer a few words and costs every reader a second pass, and a reader who gives up on the second pass guesses.
A subject, a verb, and one idea per sentence let the reader check the comment against the code in one pass.

### Examples

#### Application: Documenting a type

**Incorrect (counterexample):**

```go
// Sends every error-level record a process logs to an error reporter as well
// as to the log stream. Error level already means "needs attention", so
// teeing it here gives every failure a route to the tracker without a second
// call that a new error site could forget.
type reportingHandler struct {
```

The first sentence has no subject.
"Every error-level record a process logs" stacks a clause inside a noun phrase, "teeing" is a coined verb, and the second sentence carries a premise, a consequence, and a benefit at once.

**Correct:**

```go
// reportingHandler sends each error-level log record to the error tracker as
// well as to the log. Code logs at error level only for failures that need a
// person's attention. So every such failure reaches the tracker, and code
// that logs an error doesn't also need to report it.
type reportingHandler struct {
```

Each sentence has a subject from the code or the reader's world, a verb right after it, and one idea.

#### Application: Documenting a field

**Incorrect (counterexample):**

```go
// attrs are the logger's With attrs, already qualified by the groups open
// when they were added.
attrs []slog.Attr
```

"With attrs" assumes the reader knows the private shorthand, "qualified" is used in a private sense, and "the groups open when they were added" stacks a clause the reader has to unpack.

**Correct:**

```go
// attrs holds the attributes added with Logger.With. Each one is already
// nested inside the groups that were open when it was added.
attrs []slog.Attr
```

#### Application: A valid short annotation

```go
timeout time.Duration // per attempt, not total
```

This phrase states the one fact a caller needs, so it needs no change.

### Validation

- Read each new or changed comment once, at normal speed.
  Mark every sentence you had to reread.
- For each marked sentence, find its subject and verb.
  Check that the subject names something in the code or the world, and that no long phrase separates the verb from its object.
- Look for clauses stacked inside a noun phrase and for sentences that join more than one reason or consequence.
  Split them.
- Check each word that isn't a code name or plain English: it must be standard for this codebase's readers, or explained where it first appears.
- A short annotation phrase, a prescribed format, or a quoted message is not a violation.
