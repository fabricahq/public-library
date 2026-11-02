---
title: "State the current model and its reasons, not how it got there"
whenToRead: "Before writing, changing, or reviewing agent instructions, guides, READMEs, glossaries, or comments that define a term or explain a convention, including when a change renames or replaces one."
impact: "MEDIUM"
impactDescription: "Decision history in guidance reads as a current obligation, makes agents reason about options that no longer exist, and grows with every change."
tags: "documentation, agents-md, comments"
---

## State the current model and its reasons, not how it got there

Write guidance as what is true now and why it holds.
Leave out when it was decided, what it replaced, and how the discussion went: version control, pull requests, and architecture decision records own that history.

### Implementation

- Define a term or convention from first principles: what it is, how it differs from its neighbors, and the reason the difference matters.
- Leave out dates, "we used to", "renamed from", "decided on", and "no longer".
- When a decision's tradeoffs matter to a reader, link its decision record instead of retelling it.
- When a change replaces a convention, rewrite the guidance in place instead of adding a note about the change.

A decision record, changelog, or release note exists to record history, so this rule doesn't apply to it.
Neither does a migration or compatibility instruction that still applies, such as an upgrade guide or a deprecated name that's still accepted: readers need the old form to find and update what they have.

### Rationale

A reader of guidance needs the model to act on.
History forces them to work out which parts still hold, and an agent may follow an option the history mentions only to reject it.
Each change also adds another paragraph of history, so the guidance grows while the model it describes stays the same size.

### Examples

#### Application: Defining a term after a rename

**Incorrect (counterexample):**

```md
On 2026-10-20 we renamed the Wiki to Brain. We first called Blueprints
"artifact templates", but decided against it after a long discussion, so
Template now means only Brain templates and Workflow templates.
```

The paragraph tells the story of the rename and leaves the reader to work out the current terms.

**Correct:**

```md
A **Brain template** is a reusable Brain structure: instantiating it once
gives a new org its starting folders and artifacts. A **Blueprint** is a
recipe for one artifact, which stays linked to it and can be regenerated
from it. A Blueprint is not a template, because it is applied repeatedly
to the same artifact rather than instantiated once.
```

The paragraph defines each term and gives the reason for the distinction, with no history.

#### Application: An upgrade guide while the old name still works

**Incorrect (counterexample):**

```md
Set `output.dir` to choose where reports go.
```

A user whose configuration still says `report_dir` can't tell that it's the same setting, or that they need to change it.

**Correct:**

```md
`output.dir` replaces `report_dir`. Version 2 still reads `report_dir` and
warns; version 3 rejects it. Rename the key in your configuration to update.
```

Keep the old name here: the instruction still applies to configurations that use it.

### Validation

Search changed guidance for dates, "used to", "renamed", "previously", "no longer", and "we decided", and review each match.
Unless it's part of a migration or compatibility instruction that still applies, remove it or rewrite it as a statement of the current model and its reason.

A link to a decision record is not a violation, and neither is a version number that states a current requirement, such as a minimum supported version.
