# Review Panel

Review a change with a panel of eight focused reviewers instead of one generalist. Each reviewer is a separate, read-only Claude Code or Codex session that checks one thing in depth. A synthesis session then reads the code behind every finding, merges the duplicates, drops the false positives, and hands you one ranked list plus the questions only you can answer. A local page shows each reviewer's status, what it's reading, its findings, and the synthesis as it lands.

| Reviewer | Checks | Runs on |
| --- | --- | --- |
| check-acceptance-criteria | The spec, its acceptance criteria, and the product decisions | Claude Opus, high effort |
| check-correctness | Concrete inputs traced through the new logic | Codex, GPT-6 Astra, high effort |
| check-security | Trust boundaries, secrets, injection, tenant isolation | Codex, GPT-6 Astra, high effort |
| check-rules | The repository's own rules and agent instructions | Claude Opus |
| check-docs | Docs that the change made wrong or left missing | Claude Opus |
| check-supportability | Errors surfaced, traceable, and recoverable | Codex, GPT-6.1 Sol, high effort |
| check-performance | Only bottlenecks unacceptably large for the change | Codex, GPT-6.1 Sol, high effort |
| check-architecture | Deep modules and simpler designs, with an alternative compared | Claude Opus, high effort |

Edit `panel.json` to change a reviewer's model or effort, and `focus/` to change what it looks for.

## Install with Trail Guide

From a project that does not already have a `fabrica` source:

```sh
trailguide project init --non-interactive
trailguide project add source fabrica \
  --repository https://github.com/fabricahq/public-library.git \
  --skills skills/review-panel \
  --non-interactive
trailguide project sync
```

This selects only this skill from the latest library release. If your project already has a `fabrica` source, add `skills/review-panel` to that source's `skills.include` list and run `trailguide project update`.

The default source follows published library releases. To try the skill before a release includes it, add `--ref main` to the source command; Trail Guide warns that this uses unreleased content.

## Use it

Invoke `/review-panel` in Claude Code or `$review-panel` in Codex, optionally naming a pull request or what to focus on. The agent starts the panel, gives you the live page's URL, and summarizes the verdict when the panel finishes. It changes no code unless you ask it to fix findings.

To run the panel yourself, from the repository you want reviewed:

```sh
python3 PATH_TO_SKILL/scripts/review_panel.py run
```

This reviews the current branch, including uncommitted changes, against `origin/HEAD`, and opens the live page. `--pr 123` reviews a GitHub pull request in a temporary worktree instead; `--context spec.md` gives reviewers acceptance criteria to judge against; `--only check-correctness,check-security` runs part of the panel. Run it with `--help` for every option.

## Requirements and cost

- macOS or Linux, Python 3.10+, and Git. No packages to install.
- Claude Code, signed in. Every session uses the login the `claude` command already has, such as a Claude subscription.
- Codex, signed in, for the four Codex reviewers. Without it, or when a Codex session fails, those reviewers run on Claude and the page says so.
- The GitHub CLI, signed in, for `--pr`.

A full run starts nine sessions (eight reviewers and the synthesis), each limited to 20 minutes; a run of the whole panel on a small pull request took about eight minutes. Reviewers read a snapshot of your branch, including uncommitted and new files, so you can keep working meanwhile. Claude reviewers can only read and search files (no shell, project settings, hooks, or MCP servers), and Codex reviewers run in Codex's read-only sandbox. Results stay in `.git/review-panel/` in the reviewed repository; nothing is posted anywhere.

## What it does not do

The panel reviews and reports. It doesn't fix findings, post comments on pull requests, or run the project's tests; ask your agent to fix findings and run the panel again on the reviewers that raised them.
