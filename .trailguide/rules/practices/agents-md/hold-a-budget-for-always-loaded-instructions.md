---
title: "Hold a size budget for always-loaded agent instructions"
whenToRead: "Before adding to, extracting from, or reviewing an always-loaded agent instruction file, such as AGENTS.md or CLAUDE.md, or adding a skill whose description every session loads."
impact: "MEDIUM"
impactDescription: "Without a budget, instruction files only grow: each addition looks cheap alone, while every session pays for all of them and follows each one less reliably."
tags: "agents-md, skills"
attribution:
  - url: https://blog.kunchenguid.com/p/your-agentsmd-is-a-neural-net
    description: "Adapts Kun Chen's token budget for a project's always-loaded memory file and skill descriptions; restated, not copied."
---

## Hold a size budget for always-loaded agent instructions

Choose a size budget for what agents load in every session, and keep within it: when an addition would exceed it, prune or move an existing entry to pay for it.
When an entry changes, rewrite or remove it instead of appending a correction.

### Implementation

- Count everything every session loads: the root instruction file, any file it imports, and each skill's description line.
  Skill bodies and nested files that load only for their directory don't count against the root budget; give a nested file its own, smaller budget.
- Record the budget where maintainers see it, such as a CI check or a line in the file's maintenance section.
  Around 5,000 tokens, about 20 KB, is a reasonable ceiling; a small project needs far less.
- Over budget, every addition names the entry it removes, shortens, or moves to a skill or nested file.
- When a fact or command changes, edit its entry in place.
  A "Note: X now does Y" line below an outdated entry leaves both for the agent to reconcile.
- Prefer shortening an entry to deleting one an agent still needs.

### Rationale

Every always-loaded token is paid in every session, and instruction following dilutes as the file grows.
Each addition is reasonable on its own, so the file grows unless something forces a trade.
A budget turns "is this worth adding?" into "is this worth more than what it replaces?", which keeps the file at the size its readers can follow.
Appended corrections leave contradictory entries, and the agent may follow the stale one.

### Examples

**Incorrect (counterexample):**

```md
- Run tests with `npm test`.
...
- Note: tests now run with `pnpm test`, not `npm test`.
```

The stale entry remains, and the correction adds a line instead of replacing one.

**Correct:**

```md
- Run tests with `pnpm test`.
```

The entry is rewritten in place, so the file stays the same size and says one thing.

### Validation

1. Estimate the always-loaded size, for example `wc -c` of the root file and its imports plus the skill description lines, divided by 4 for tokens, and compare it with the budget.
2. For a change that adds lines while over budget, confirm it removes, shortens, or moves at least as much.
3. Look for entries that correct or contradict an earlier entry, and merge them.

A file over budget is not a violation when the change shrinks it.
A section a tool generates counts toward the size but is changed through that tool, not by hand.
