---
name: setup-pr-10k
description: "Declare a repository's layers once, check them in CI, and keep them current: discover the layers from the import graph, have the user approve them, write them as a go-arch-lint file with a purpose and a review marker for each layer, and add the checks to CI. Use when asked to set up PR 10K or pr-10k, to declare, document, or enforce a repository's layers or architecture, or when CI's layer check fails because a layer's purpose, packages, or review marker are out of date. Supports Go; TypeScript is not supported yet."
metadata:
  trailguide-skill-type: playbook
---

# Set up PR 10K

PR 10K shows a pull request's interface changes layer by layer, so a
reviewer can see what a change does to the system before reading its code.
It reads the layers from a file the repository keeps, not from a guess at
review time. This skill writes that file, adds the checks that keep it true,
and later brings it up to date.

A repository is set up when it has:

1. A `.go-arch-lint.yml` whose components are the layers. Each one carries a
   `# purpose:` line saying what belongs in it and a `# reviewed:` line
   naming the commit where someone last confirmed the purpose still matches.
2. A CI job that runs [go-arch-lint](https://github.com/fe3dback/go-arch-lint)
   and [`scripts/check-layers.go`](scripts/check-layers.go) on every pull
   request.
3. One line in `AGENTS.md` pointing to the layer file.

If `.go-arch-lint.yml` already exists, skip to [Update the layers](#update-the-layers).

The layer check, `scripts/check-layers.go`, runs with the Go standard library
alone. Run it with `--help` before anything else; it owns what a stale layer
is and how to clear one. Run it from wherever this skill is installed, such as
`.agents/skills/setup-pr-10k/scripts/check-layers.go`.

## Set up a Go repository

### 1. Read the import graph

From the module root, list each package and the module's own packages it
imports:

```sh
mod=$(go list -m)
go list -f '{{.ImportPath}}: {{join .Imports " "}}' ./... | sed "s|$mod/||g"
```

Read every package's doc comment too: it usually says what the package owns.
For a picture to show the user, `go run github.com/loov/goda@v0.10.2 graph
-cluster -short ./... | dot -Tsvg -o layers.svg` draws the same graph.

### 2. Propose layers, and get the user's approval

Group the packages into layers. A layer is a set of packages whose purpose
fits in one sentence and whose imports point the same way. Aim for four to
eight layers; most repositories have an entry point, commands, the domain's
core logic, configuration, adapters to the outside world, shared core types,
and test doubles. Name each layer for what it is to this repository, not for
a textbook pattern it doesn't follow.

Take each layer's allowed dependencies from the imports the code has today,
not from an ideal. Where an import runs against the direction the rest of
the code follows, show it to the user as a question rather than writing it
as a rule.

Show the user one table: each layer's name, its purpose, its packages, and
the layers it may import. List every import that crosses layers against the
grain, and say what you recommend for each. Write nothing until the user
approves the table; the layers are theirs to decide.

### 3. Write `.go-arch-lint.yml`

Follow this shape. Each component lists itself in `mayDependOn` when its own
packages import each other. Test files may import anything, so they're
excluded.

```yaml
# This repository's layers, checked by go-arch-lint on every pull request and read by pr-10k.
# Each component is a layer. Its "purpose" line says what belongs there; its "reviewed" line names the
# commit at which someone last confirmed that purpose and those packages still match.
version: 3
workdir: .
allow:
  depOnAnyVendor: true
excludeFiles:
  - "^.*_test\\.go$"
components:
  # purpose: The binary's main package; it only hands control to the commands.
  # reviewed: 1a2b3c4
  entry:
    in: cmd/app
  # purpose: Everything that talks to the outside world.
  # reviewed: 1a2b3c4
  adapters:
    in: [internal/github, internal/store]
deps:
  entry:
    mayDependOn: [adapters]
  adapters:
    mayDependOn: [adapters]
```

Set every `# reviewed:` to the short commit of the default branch you
started from (`git rev-parse --short origin/main`), never a commit on your
branch: a squash merge drops those.

Then run both checks:

```sh
go run github.com/fe3dback/go-arch-lint@v1.19.1 check
go run path/to/check-layers.go
```

go-arch-lint fails on any package no component holds, and on any import the
`deps` don't allow. It has no baseline, so for each import that breaks the
approved layers, either fix the import in its own commit or allow the edge
with a comment above it saying it is a known exception and why. Never widen a
layer's dependencies silently to get green.

### 4. Add the checks to CI

Add one job to the repository's CI, beside its other Go checks. The layer
check counts commits, so it needs the full history. For GitHub Actions:

```yaml
  layers:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          fetch-depth: 0
      - uses: actions/setup-go@v5
        with:
          go-version-file: go.mod
      - run: go run github.com/fe3dback/go-arch-lint@v1.19.1 check
      - if: github.event_name == 'pull_request'
        run: go run .agents/skills/setup-pr-10k/scripts/check-layers.go --base "origin/$GITHUB_BASE_REF"
```

Match the repository's own runner, action versions, and step style rather
than copying this one. With `--base`, a stale layer fails only the pull
requests that change it.

### 5. Point to the layers from `AGENTS.md`

Add one line, near the repository's other guidance:

```md
Layers: [`.go-arch-lint.yml`](.go-arch-lint.yml) declares this repository's layers and what belongs in each; CI checks them.
```

Don't restate the layers there. The file and its checks are the source.

### 6. Hand back

Open one pull request with the layer file, the CI job, the `AGENTS.md` line,
and any import fixes. In its description, show the approved table and each
known exception.

## Update the layers

Do this when the layer check fails, when go-arch-lint reports a package no
layer holds, or when the user asks to revisit the layers.

1. Run `check-layers.go` (with `--base` on a branch) and go-arch-lint
   `check`. Each stale layer comes with its purpose, its packages, the
   commits since its review, and the files added or deleted.
2. For each stale layer, read the commits' subjects and the new or deleted
   files, and the doc comment of each package in the layer. Decide whether
   the purpose still describes every package.
3. If it does, set its `# reviewed:` to the commit the check prints. You may
   do this yourself; say in the pull request which layers you confirmed.
4. If it doesn't, propose the change to the user, as in step 2 of the setup:
   a new purpose, packages moved between layers, a layer split, merged,
   added, or removed, and the `deps` that follow. Make the change only once
   they approve, then mark every layer you changed as reviewed.
5. Put a new package in the layer its purpose fits. If none fits, that is a
   new layer, and the user's call.
6. Run both checks again and commit the layer change on its own.

## TypeScript

Not supported yet. TypeScript layers will live in `.dependency-cruiser.layers.cjs`,
read by both [dependency-cruiser](https://github.com/sverweij/dependency-cruiser)
and PR 10K. Until then, tell the user this skill covers Go only.
