# Fabrica Public Library agent guide

This repository is a [Trail Guide](https://github.com/fabricahq/trailguide) library. The `library` section of `.trailguide/config.yaml` is its manifest; groups and rules live in `.trailguide/rules/`, shared files in `.trailguide/assets/`, and change notes in `.trailguide/changes/`. The [README](README.md) explains what it contains and how to contribute.

Use the Trail Guide version that `.github/workflows/trailguide.yml` pins, so your checks match CI.

## Rules

Write and revise rules with the [Trail Guide rule rubric and template](https://trailguide.fabricahq.com/reference/rule-authoring/). When you add, remove, rename, or retitle a rule or group, update the README's rule count badge, group table, rule lists, and install command to match.

## Skills

Skills live in `.trailguide/skills/<origin>/`: the library's own in `skills/fabrica/`, and each fork in the folder named for its source, such as `skills/pstack/`. `build` follows the Build stage of [the Fabrica book](https://fabricahq.com/book) and calls skills from [pstack](https://github.com/cursor/plugins/tree/main/pstack). The `pstack` source in `.trailguide/config.yaml` pins a `cursor/plugins` commit, because its skills go straight into agents' build instructions: pstack's changes reach projects only when the library moves the pin and publishes a library release. Curate a pstack skill only when one of the library's skills calls it, list it under `library.skills.dependencies` so it installs only with the skills that call it, and leave out any skill that picks subagent models or depends on Cursor-only paths or services. The library's own skills take change notes the way rules do, as [Change notes](#change-notes) describes; curated skills need none.

`show-me-your-work`, `create-verification-skill`, and `maintain-verification-skill` are local forks recorded under the `pstack` source's `skills.forks`. The verification skills are independently recommended; their mutual follow-up suggestions are not calls. Declare each skill's direct calls in `trailguide-skills-used` so Trail Guide resolves transitive dependencies; do not infer calls from every skill name mentioned in prose. To move the pin, read each curated skill's changes at the new commit against the criteria above, port the changes that fit from each local fork's upstream diff that `trailguide library check` then lists, and update the commit in NOTICE.md. When you add or drop a skill, update the README's skills section and NOTICE.md to match.

## Change notes

Each rule has its own version, and library releases publish rule changes to projects. Once the library has published its first library release, a `release/1` tag, every new, changed, or retired rule needs a change note in `.trailguide/changes/`. Record it with `trailguide library change` in the same pull request as the rule change:

- **Changed rule:** `trailguide library change RULE_ID --bump major|minor|patch --summary '...'`. Choose the level from what the change does to the rule's obligation, as `trailguide library change --help` defines it. When unsure, choose the larger level.
- **New rule:** `trailguide library change RULE_ID --summary '...'`. A new rule starts at version 1.0.0, so it takes no `--bump`.
- **Retired rule:** delete the rule's Markdown file and asset directory, then run `trailguide library change RULE_ID --retire --summary '...'`, adding `--replaced-by NEW_RULE_ID` when another rule replaces it. A rename or move retires the old ID and adds the new one; see [Rename a rule](https://trailguide.fabricahq.com/guides/version-rules/#rename-a-rule).

Write each summary as one line for project maintainers deciding whether to update: what changed in the obligation or guidance, not how you edited the file. Group descriptions in `_group.yaml` and shared files in `.trailguide/assets/` are library-wide and need no note. Change notes stay in `.trailguide/changes/` permanently; to reword one before it's published, edit it. See [Version your rules](https://trailguide.fabricahq.com/guides/version-rules/) for the full workflow.

## Validate

Before you push, run these from the repository root:

```sh
trailguide library check
uv run .github/scripts/check-readme.py
```

`trailguide library check` fails when a rule change is missing a note or a note doesn't match a change, and otherwise previews the pending library release. The **Trail Guide** and **README** workflows run these checks on every pull request.

## Library releases

The maintainer publishes library releases with `trailguide library release`, which tags `release/<number>` and creates the GitHub Release page. Your part ends at the pull request: you may preview a library release with `trailguide library release --dry-run`, and leave publishing, `release/*` tags, and GitHub Release pages to the maintainer.
