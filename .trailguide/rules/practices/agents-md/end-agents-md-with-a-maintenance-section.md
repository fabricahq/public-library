---
title: "End AGENTS.md with a section on maintaining it"
whenToRead: "When creating a project's AGENTS.md, or reviewing one that lacks a section saying how to maintain it."
impact: "MEDIUM"
impactDescription: "Agents edit AGENTS.md as often as people do, and without the bar written in the file, each edit appends to it and restates what the code already shows."
tags: "agents-md"
attribution:
  - url: https://github.com/kunchenguid/runner-up/blob/main/AGENTS.md
    description: "Kun Chen's 'Maintaining this file' footer, quoted verbatim from his repositories (runner-up and backpass) as a starting template projects may adapt; MIT License, Copyright (c) 2026 Kun Chen, notice retained in NOTICE.md."
  - url: https://blog.kunchenguid.com/p/your-agentsmd-is-a-neural-net
    description: "Kun Chen's guidance for a short AGENTS.md. The maintenance footer this rule quotes verbatim is his recommended starting template, not required wording."
---

## End AGENTS.md with a section on maintaining it

End the hand-written part of a project's AGENTS.md with a short section on how to maintain the file.
A section a tool generates may follow it.
The section states four principles, in the project's own words:

- Keep an entry only when it is useful to almost every session, or when violating it is costly.
- Point to the authoritative file, command, or test instead of repeating what the codebase shows.
- Rewrite or prune an existing entry instead of appending.
- Keep entries concise.

The costly-to-violate case has to be explicit in this section. A later agent may see only the footer, and the keep rule's exception for a safety or other high-consequence fact has to reach that agent here.

Kun Chen's footer is a recommended starting template, quoted verbatim from his repositories:

```md
## Maintaining this file

Keep this file for knowledge useful to almost every future agent session in this project.
Do not repeat what the codebase already shows; point to the authoritative file or command instead.
Prefer rewriting or pruning existing entries over appending new ones.
When updating this file, preserve this bar for all agents and keep entries concise.
```

Those four sentences do not name the costly-to-violate exception. A project adapts the wording and adds it.

### Implementation

- A project note, such as the size budget, can be a line in the section.
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

Keep an entry only when almost every session needs it, or when violating it is costly, such as where a secret may travel.
Point to the file, command, or test that owns a fact instead of repeating what the code shows.
Rewrite or prune an existing entry instead of appending one, and keep each entry short.
```

This is one adaptation of the template. It adds the exception the template leaves out.

### Validation

1. The hand-written part of the root AGENTS.md ends with a short section that states all four principles, including that an entry costly to violate stays.
2. Only a tool-generated section follows it.
3. An existing policy that states the same four principles in different words complies. Matching the template's sentences, or its heading, is not required.
