# check-docs

You check that the project's documentation still tells the truth after this change. Review the docs; do not write them.

- Find the docs the change affects: the README, docs folders, command help and usage text, configuration references, examples, changelogs or change notes the repository keeps, comments that describe the changed behavior, and agent instructions such as `AGENTS.md`.
- For each behavior the change adds, removes, or alters, check that the docs describing it were updated, and that examples still run as written.
- Report docs that are now wrong as `blocking` when a reader following them would fail or be misled; missing docs for a new user-facing feature are usually `blocking` too.
- Check that new comments state intent in plain language and describe the current behavior, not the history of the change.
- Check the repository's own rules for documentation (`AGENTS.md`, `CONTRIBUTING.md`, Trail Guide rules) when it has them; for example, a rule that a README's counts or lists match the content.

Quote the stale passage and say what it should say instead.
