---
title: "End AGENTS.md with a section on maintaining it"
whenToRead: "When creating a project's AGENTS.md, or reviewing one that lacks a section saying how to maintain it."
impact: "MEDIUM"
impactDescription: "Agents edit AGENTS.md as often as people do, and without the bar written in the file, each edit appends to it and restates what the code already shows."
tags: "agents-md"
attribution:
  - url: https://github.com/kunchenguid/runner-up/blob/main/AGENTS.md
    description: "The 'Maintaining this file' footer is Kun Chen's text, quoted verbatim from his repositories (runner-up and backpass); MIT License, Copyright (c) 2026 Kun Chen, notice retained in NOTICE.md."
  - url: https://blog.kunchenguid.com/p/your-agentsmd-is-a-neural-net
    description: "Kun Chen's guidance for a short AGENTS.md; the maintenance footer this rule quotes is his text, quoted verbatim from his repositories."
---

## End AGENTS.md with a section on maintaining it

Close a project's AGENTS.md with this section, word for word. These four sentences are Kun Chen's text, quoted verbatim from his repositories:

```md
## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
```

### Implementation

- Make it the last section of the text the project writes, after every entry.
  A section a tool generates and keeps current may follow it.
- Keep the wording unchanged, so every repository states the same bar and a reviewer can check it at a glance.
- Put project-specific maintenance notes, such as a size budget, in a line after the four sentences, not in place of them.
- A nested AGENTS.md doesn't need its own copy; the root file's section covers every file in the repository.

### Rationale

Agents are the most frequent editors of AGENTS.md, and they read the file before editing it.
A bar written in the file reaches every agent that edits it, whatever the harness or the request, so it keeps entries short and on point without anyone repeating the instruction.
Placing it last means it is read after the entries it governs and isn't displaced as entries are added above it.

### Examples

**Incorrect (counterexample):**

```md
# Agent guide

## Commands

- `make test`
```

Nothing tells the next agent what belongs in the file, so it adds whatever its task taught it.

**Correct:**

```md
# Agent guide

## Commands

- `make test`

## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
```

### Validation

1. The root AGENTS.md has a `## Maintaining this file` section containing the four sentences above, unchanged.
2. No entry of the project's own follows that section; only a tool-generated section may.
