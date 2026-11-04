---
title: "Keep AGENTS.md to what almost every session needs and can't see"
whenToRead: "Before adding an entry to, pruning, or reviewing an always-loaded agent instruction file, such as a root or nested AGENTS.md, including when a change alters a command, directory, or invariant that file describes."
impact: "MEDIUM"
impactDescription: "Entries that restate the code or matter to a few tasks dilute the ones every task needs, and copies of what other files own go stale without anything failing."
tags: "agents-md"
attribution:
  - url: https://blog.kunchenguid.com/p/your-agentsmd-is-a-neural-net
    description: "Draws on Kun Chen's guidance that a project AGENTS.md holds only what almost every session needs, with narrow material moved to skills; restated, not copied."
---

## Keep AGENTS.md to what almost every session needs and can't see

Put an entry in an always-loaded agent instruction file only when almost every agent session in that directory needs it and the agent can't get it quickly from the code, or when breaking it would be costly.
For anything an existing file, command, or test already states, write a pointer to that owner instead of a copy.

### Implementation

- **Keep:** one or two sentences on what the project is; a map of the places an agent can't guess, each with its role; the exact commands to build, test, and lint, including a faster or narrower form and any command with a trigger, such as "after changing `go.mod`"; invariants an agent can't see from the file it is editing, such as where secrets may travel; and the gate a change must pass to merge.
- **Point instead of copying:** name the owner in one clause, such as "see README.md, 'Setup'" or "`src/cli.js` is the authoritative flag list."
- **Leave out:** what reading the code shows, such as a full directory tree, a flag table, or a convention every file already follows; advice the agent follows without being told, such as "write clean code"; and a reaction to one incident that hasn't recurred.
- **Move narrow material out:** a procedure most sessions don't need, such as cutting a release, goes in a skill whose description names when to use it, the document that owns it, or a nested AGENTS.md for the directory it concerns.
  Leave at most one line behind, and only when the step is easy to miss and costly to skip.
- **Write each entry as one plain instruction or fact,** without emphasis such as IMPORTANT or capitals.

A safety-critical entry stays even when few sessions need it.

### Rationale

Harnesses load the root instruction file into every session, and instruction following weakens as the file grows.
Most of what a long file says is either discoverable from the code, which agents read anyway, or relevant to a few tasks, so it dilutes the entries every task needs.
A skill's description costs one line per session and its body loads only when the task calls for it, so a narrow procedure costs far less there.
A copy of what another file owns goes stale when that file changes, and nothing fails to say so; a pointer stays true as long as the owner exists.

### Examples

#### Application: Commands and layout

**Incorrect (counterexample):**

```md
## Project structure

- cmd/
  - root.go
  - serve.go
- internal/
  - agent/
  - config/

## Guidelines

- IMPORTANT: Always write clean, well-tested code.
- The CLI accepts --config, --verbose, --dry-run, --timeout, ...
```

The tree repeats what `ls` shows, the guideline tells the agent what it already does, and the flag list duplicates the CLI's help and will drift from it.

**Correct:**

```md
## Layout

- `internal/coordinator/` - the serve loop (`serve.go`), placement, and self-update (`update.go`)
- `internal/testrun/` - tests start every program with `testrun.Command` and give every wait a deadline

## Commands

- `make build`, `make test`, `make lint`
- `go test -short ./...` skips the tests that run the binary
- `nix build .#default` after changing `go.mod` or `go.sum`; `vendorHash` in `package.nix` must match
```

Each layout line says what a directory is for or a convention the agent must follow there, and each command is exact, including when to run the conditional one.

#### Application: A procedure few sessions need

**Incorrect (counterexample):**

A 40-line "Cutting a release" section in AGENTS.md, in a repository where most sessions fix bugs or add features.

**Correct:**

```md
- Before merging a release PR, run `make test-real-tart` on a Mac with Tart (CONTRIBUTING.md, "Before a release").
```

The steps live in CONTRIBUTING.md or a release skill.
The file keeps one line, because the step is easy to miss and costly to skip.

### Validation

For each new or changed entry, check:

1. Would an agent need it in almost every session in this directory, or is breaking it costly?
2. Could the agent get it from the code, and would it reliably look there? If both, remove it.
3. Does another file, command, or test own it? If so, the entry names the owner in one clause rather than restating it.
4. Does each command run as written from the stated directory?

A rarely relevant entry is not a violation when breaking it is costly, such as where secrets may be stored.
A nested AGENTS.md is judged against the sessions that work in its directory, not the whole repository.
A section a tool generates and maintains, such as an index of rules or skills, is judged by that tool's owners, not edited by hand.
