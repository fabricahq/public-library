---
title: "Keep instructions in AGENTS.md, and import it from CLAUDE.md"
whenToRead: "When creating or reviewing a CLAUDE.md or another harness-specific instruction file in a repository that has, or should have, an AGENTS.md."
impact: "LOW"
impactDescription: "Two full instruction files drift apart, so agents in different harnesses follow different rules; a symlink or a 'see AGENTS.md' line loads less reliably than an import."
tags: "agents-md, claude-code"
attribution:
  - url: https://blog.kunchenguid.com/p/your-agentsmd-is-a-neural-net
    description: "Follows Kun Chen's recommendation to keep AGENTS.md canonical and make CLAUDE.md a one-line import; restated, not copied."
---

## Keep instructions in AGENTS.md, and import it from CLAUDE.md

Write a directory's agent instructions once, in its AGENTS.md.
Make the CLAUDE.md beside it contain only the import line `@AGENTS.md`, not a symlink, a copy, or a sentence telling the agent to read AGENTS.md.

### Implementation

- Move anything a CLAUDE.md says beyond the import into AGENTS.md, then reduce CLAUDE.md to `@AGENTS.md`.
- A comment above the import, such as `<!-- Edit AGENTS.md, not this file. -->`, is fine; instructions are not.
- Do the same for a nested CLAUDE.md beside a nested AGENTS.md.

### Rationale

Codex, Cursor, and most other harnesses read AGENTS.md, and Claude Code reads CLAUDE.md, so one file has to serve all of them.
Claude Code inlines an `@` import when it loads the file, so the instructions arrive in every session.
A "see AGENTS.md" sentence relies on the agent choosing to open the file, a symlink breaks on checkouts and tools that don't preserve links, and a second full file drifts.

### Examples

**Incorrect (counterexample):**

```md
# CLAUDE.md

See AGENTS.md for project instructions.
```

**Correct:**

```md
@AGENTS.md
```

### Validation

1. Each CLAUDE.md that sits beside an AGENTS.md contains `@AGENTS.md` and nothing else but blank lines, headings, or comments.
2. CLAUDE.md is a regular file, not a symlink.
