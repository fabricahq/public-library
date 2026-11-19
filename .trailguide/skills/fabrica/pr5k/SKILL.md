---
name: pr5k
description: Build PR5K, a 5,000-foot view of a pull request on one canvas, so a reviewer sees its big picture before its details. Use when someone wants to review a PR's schema changes, entities, architecture decisions, design-principle fit and verification rather than its lines.
metadata:
  trailguide-skill-type: review
  display-name: PR5K
  short-description: Review the big picture of a pull request
  default-prompt: Use $pr5k to show me the big picture of this pull request.
---

# PR5K

PR5K is the 5,000-foot view of a pull request: high enough to see the shape of the change, low enough to make out its tables, entities and decisions.

Help a reviewer understand a pull request: what it created, what it changed, how the pieces relate, and how it was verified. This is not a bug review. Never report defects as findings; adversarial code review covers that. Describe what is there, with literal examples, so the reviewer gets a feel for how it works.

The output is one self-contained page: a section rail, a pannable canvas, and an inspector that opens when a node is clicked. You write a JSON snapshot; the bundled script renders it.

## Gather

1. Read the PR: title, body, base and head branches, the stack it sits on, stats, commits, review comments and CI status. Read the repository's planning or decision records the PR touches; they are the best source for why.
2. Diff base against head. Work from the merge base (`git diff base...head`).
3. If you are the agent that built the PR, collect your own verification from this session. Otherwise take it from the PR body, commits and comments, and say so in `verification.agentNote`.
4. Read the project's personas from `.pr5k/settings.yaml` at the repository root and copy them into the snapshot's `personas`, so the page's Settings window shows them. Use them to write descriptions in the product's own terms: name a persona when a change matters to particular people ("Field agents can now..."), and otherwise say "users". If the file is missing, say "users"; never invent personas.

## Sections

Write each section that has content. Leave a section out rather than inventing it.

- **database**: every table the PR creates or changes, plus the unchanged tables they reference, shown as context. Get the schema by running every migration on a fresh database at the base and at the head and diffing the dumps; never reconstruct columns from reading migrations alone. For each table say what one row is in a few words (`row`, such as "One task, assignable to a person."), what the PR changes as short bullets (`explain`, a list), each column's status (`new`, `changed`, `renamed` with `from`, `removed`, `same`), listing every column of every table shown, context tables and unchanged columns too, one entry per column, so the board and the chat show what a row holds, the column it references (`ref`), the values a check constraint allows (`values`, with the constraint's name in `valuesRule`), its constraints and access policies in plain words, and the migrations that touch it. Write example rows with realistic values that show each new column doing its job, load them into the head database, and keep only rows it accepts. Try at least one row each new constraint should refuse and confirm it does. When a migration rewrites existing data, insert a row at the base, run the PR's migrations over it, and show it before and after in `dataMigration`, naming the table it belongs to in `table`.
- **backend**: new and changed types, enums, views, rules, store interfaces and API operations, grouped by what they are for. Give every property of a changed type, unchanged ones marked `same`, with its status (`renamed` with `from`), a one-line meaning and any fixed set of `values`, and a JSON example that matches the database example where they overlap.
- **frontend**: new and changed components, hooks and the modules that own a decision. Say where each shows, what it takes, and a short example. Mark hand-drawn text examples `"lang": "text"`, which the page labels as a sketch.
- **architecture**: decisions that change how the system is shaped. Each has before, after, why, trade-off and its source, and a small `diagram` of the before and the after: rows of boxes, `→ label` arrows and stacks, with boxes toned `new`, `changed`, `removed` or `muted` (see the example).
- **principles**: rate the PR against each principle in [references/principles.md](references/principles.md) as `strong`, `mixed` or `weak`, with a one-line verdict and concrete evidence from this PR. List each red flag with whether you saw it and where. For each one you saw, draw the `issue` the same way as a decision's diagram and propose a simple `fix`, with its text and diagram. Rate design, not correctness.
- **verification**: runs of any `verify-*` skill (what was walked, what it found, what was fixed), the checks that ran and their results, what was found and then fixed during the work with commit references, and what was not verified. Add what you did to check the canvas itself.
- **media**: screenshots and recordings from the PR, its preview build or its showcase runs. Embed images you can read as `data:` URIs in `src`; link the rest. The canvas works without media.
- **overview**: a headline and what users can now do. Group it by the system's own things, such as Tasks or Workflows, then by subgroups within each (`group`, `icon`, `subgroups` of `group` and `items`). Name each subgroup for what people can now do, as a short verb phrase such as "Track status" or "View and assign teammates' work", never a bare noun.

## Render and deliver

1. Write the snapshot to match [examples/invoice-installments.json](examples/invoice-installments.json), a made-up PR that uses every field. Keep example ids and names consistent across sections, and list them in `people` so the page can name the person beside each id.
2. Render it: `python3 scripts/render.py SNAPSHOT.json OUT.html`.
3. Open the page in a browser once and check that the schema view lays out without overlapping tables, then give the reader the page.
4. When you publish it as a claude.ai Artifact, declare `capabilities: {"sample": {}, "comments": {}}`. The reader can then chat about the PR from the toolbar, or highlight any text and ask about it: Claude answers in a bubble from the snapshot alone, so the page never waits on you. Each answer names the parts of the snapshot it used, as links to their windows, and "See Claude's context" lets the reader browse and search the snapshot itself, so its limits are visible. A question that needs the code goes to you as a comment on the highlighted text; you are woken by it, answer from the repository in that comment thread, and never poll for questions. Opened as a plain file, the page works without asking.

Write for someone who has not read the code: plain sentences, the product's own words, no em dashes. Prefer short bullets under a plain heading to a paragraph.

Never show a list of more than five items flat. Group it under short headings, with at most five items in a group: in the overview by the system's own things (see **overview**), and for verification runs by a `group` on each run.

Put field, column, type and operation names in backticks, such as `description` or `tasks.create`; the page shows them as code.
