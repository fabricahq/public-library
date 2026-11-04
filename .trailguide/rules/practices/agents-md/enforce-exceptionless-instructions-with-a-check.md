---
title: "Enforce an instruction that has no exceptions with a check"
whenToRead: "When adding or reviewing an agent instruction that states an absolute rule, such as never, always, or must, or when agents repeatedly break an instruction the file already states."
impact: "MEDIUM"
impactDescription: "An agent can miss or misread any instruction, so a rule that must always hold breaks silently; emphasis grows the file without making the rule hold."
tags: "agents-md, ci, linting"
attribution:
  - url: https://openai.com/index/harness-engineering/
    description: "Follows OpenAI's harness-engineering guidance to enforce invariants mechanically rather than by instruction; restated, not copied."
---

## Enforce an instruction that has no exceptions with a check

When an agent instruction must always hold and a test, lint rule, type check, CI job, or hook can verify it, add that check, and keep one line in the instruction file that states the rule and names the check.

### Implementation

- Write the check so it fails with a message that says what to do, since the agent reads that message when it trips.
- Replace the instruction's explanation, history, and emphasis with one line: the rule and the check that guards it.
- When agents keep breaking an instruction, make it a check or shorten the file around it; don't add capitals, IMPORTANT, or repetition.
- Keep an instruction no check can verify, such as a judgment about design, as a plain line.

### Rationale

Instructions are followed most of the time, and a check holds every time, including when the agent never read the line.
A failing check also catches people and agents who don't read the file.
The remaining line costs little and tells the agent why the check exists, so it fixes the cause instead of working around the check.

### Examples

**Incorrect (counterexample):**

```md
NEVER add `paths` or `paths-ignore` to the CI workflow!!! GitHub skips a
workflow filtered by paths, and a required check that never runs leaves the
pull request blocked forever. This happened in March when someone ...
```

**Correct:**

```md
- A workflow backing a required check must not use `paths`/`paths-ignore`; the tests in `internal/ciguard` guard it.
```

The rule is one line, and it names the test that enforces it, so the agent knows where a failure comes from.

### Validation

1. For each absolute instruction, ask whether a test, lint rule, CI job, or hook could verify it; if so, a check exists and the line names it.
2. The instruction file uses no emphasis, such as capitals or IMPORTANT, to make a rule stick.

An absolute instruction without a check is not a violation when no practical check can verify it.
