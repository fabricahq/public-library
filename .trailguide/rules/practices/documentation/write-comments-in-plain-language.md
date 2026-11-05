---
title: "Write comments in plain, direct language"
whenToRead: "Before writing, changing, or reviewing a code or configuration comment, such as a file header, package, type, function, or field documentation, or a comment inside a function body. Use this rule, not the Writing group's rules, for the prose of any comment or docstring."
impact: "MEDIUM"
impactDescription: "A comment that readers must parse twice slows every later change to its code, and one they misread leads people and agents to change the code wrongly."
tags: "comments, documentation, writing"
---

## Write comments in plain, direct language

Write comments so the reader gets their meaning without decoding the prose.
Make the relevant actor, action, condition, and consequence clear.
Keep related words close together, and split sentences when their structure obscures the meaning.
Use names from the code and familiar technical terms; explain project-specific shorthand.

### Implementation

- Make clear what acts and what it does.
  Naming the type, function, caller, or service as the subject is the usual way ("reportingHandler sends"), but not the only one.
  Lead with a condition when it frames a contract ("If the context is canceled, Wait returns `ctx.Err()`"), and use an imperative for a warning or an instruction ("Do not retry after a partial write", "Exempt X from Y because Z").
  Follow the language's doc-comment convention where one exists, such as Go's starting with the identifier.
- Keep related words close together.
  A long phrase wedged between a verb and its object, as in "hands records, with the attrs and groups the logger accumulated, to reporter", makes the reader hold the sentence open.
  Move the phrase into its own sentence or after the object.
- Unpack phrases that hide their structure, such as a clause stacked inside a noun phrase ("every error-level record a process logs").
  Adding "that" or reordering is often enough.
- Keep closely related ideas together.
  A premise and its consequence usually read best joined by "because" or "so."
  Split a sentence when it carries several ideas and its structure hides how they relate, not because it has more than one clause.
- Use names from the code for code, and familiar technical terms for general ideas, such as "tee", "idempotent", or "mutex."
  Explain project-specific shorthand, and words the project uses in a narrower sense than usual.
  When a general word could mean several things here, such as "qualified", say what applies to what.
- Leave a clear comment alone.
  Don't rewrite a comment that reads well on the first pass only to match the patterns in this rule.

### Exceptions

- A short annotation can be a phrase, such as a field's unit (`// in seconds`) or a value's meaning (`// per attempt, not total`).
- Leave formats that a tool or law prescribes as they are, such as license headers, build tags, generated-code markers, and lint directives.
- Quote an error message, protocol text, or upstream comment exactly.
- Terms that every reader of this codebase knows, such as its domain vocabulary, need no explanation.

### Rationale

People read a comment in the middle of a task, to confirm what code promises before they change it.
Agents read it the same way, and act on what they take it to mean.
A compressed or tangled sentence saves the writer a few words and costs every reader a second pass, and a reader who gives up on the second pass guesses.
The fix is whatever makes the meaning clear, not a fixed sentence shape: a condition-first contract or an imperative warning is often the clearest form.

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

The first sentence doesn't say what sends, and "every error-level record a process logs" stacks a clause inside a noun phrase.
The second sentence restates a project-wide logging convention, then states its benefit as a negation ("without a second call that a new error site could forget") that the reader has to turn around.
"Teeing" is a standard term and isn't the problem.

**Correct:**

```go
// reportingHandler sends error-level records to both the log and the error
// tracker, so callers don't need a separate reporting call.
type reportingHandler struct {
```

The comment says what acts, what it does, and what that gives callers, in one sentence joined by "so."

#### Application: Documenting a field

**Incorrect (counterexample):**

```go
// attrs are the logger's With attrs, already qualified by the groups open
// when they were added.
attrs []slog.Attr
```

"With attrs" is private shorthand, "qualified" doesn't say what is done to the attributes, and "the groups open when they were added" stacks a clause the reader has to unpack.

**Correct:**

```go
// attrs holds the attributes added with Logger.With. Each one is already
// nested inside the groups that were open when it was added.
attrs []slog.Attr
```

#### Application: Clear comments in other shapes

```go
// If the context is canceled, Wait returns ctx.Err().
func (g *Group) Wait(ctx context.Context) error

// Do not retry after a partial write.
n, err := w.Write(buf)

timeout time.Duration // per attempt, not total
```

A condition-first contract, an imperative warning, and a short annotation each read clearly on the first pass, so none needs a change.

### Validation

- Read each new or changed comment once, at normal speed.
  Mark every sentence you had to reread.
- For each marked sentence, find what obscured it: an unclear actor, action, condition, or consequence; related words pulled apart; a phrase that hides its structure; several ideas whose relationship is unclear; or a term the reader may not know.
  Fix that, and only that.
- Check each term that isn't a name from the code: it must be a familiar technical term, standard for this codebase's readers, or explained where it first appears.
- A sentence that reads clearly on the first pass is not a violation, whatever its structure.
  Neither is a short annotation phrase, a prescribed format, or a quoted message.
