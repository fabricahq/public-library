# Review Panel

Review a change with a panel of eight focused reviewers instead of one generalist. Each reviewer is a separate, read-only Claude Code or Codex session that checks one thing in depth. A synthesis session then reads the code behind every finding, merges the duplicates, drops the false positives, and hands you one ranked list plus the questions only you can answer. A local page shows each reviewer's status, what it's reading, its findings, and the synthesis as it lands.

| Reviewer | Checks | Runs on |
| --- | --- | --- |
| check-acceptance-criteria | Checks the change against the known acceptance criteria and product decisions | Claude Opus, high effort |
| check-correctness | Traces concrete inputs through the new logic to find wrong results | Codex, GPT-6 Astra, high effort |
| check-security | Checks trust boundaries, secrets, injection, and tenant isolation | Codex, GPT-6 Astra, high effort |
| check-rules | Checks the change against the repository's own rules and agent instructions | Claude Opus |
| check-docs | Checks that the docs still match the code after this change | Claude Opus |
| check-supportability | Checks that failures surface, can be traced, and can be recovered | Codex, GPT-6.1 Sol, high effort |
| check-performance | Flags only bottlenecks too large for the change's real workload | Codex, GPT-6.1 Sol, high effort |
| check-architecture | Judges whether the design is as simple as it could be, and proposes a simpler one | Claude Opus, high effort |

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

## Customize the panel for a repository

A repository changes its panel with a folder of plain files, `.fabrica/review-panel/`, so everyone who runs the panel there gets the same reviewers:

```text
.fabrica/review-panel/
├── panel.yaml              which reviewers run, in what order, and the synthesis model
└── reviewers/
    ├── check-security.md   replaces or extends a built-in reviewer
    └── check-payments.md   adds a new reviewer
```

Each reviewer file is that reviewer's focus prompt in Markdown, with `summary`, `harness` (`claude-code` or `codex`), `model`, and `effort` in its front matter. A file named after a built-in reviewer replaces its prompt, or adds to it with `mode: append`. Any other name adds a reviewer, which needs a `summary`. `panel.yaml` is optional: its `reviewers` list picks and orders the panel, and its `synthesis` map sets the synthesis model. Without a list, every built-in reviewer runs, plus every file in `reviewers/`.

The panel reads this folder from the checkout it runs in, never from a pull request under review, so a change can't rewrite the panel that judges it. `--panel DIR` reads another folder for one run. The page's settings window shows each reviewer's prompt, lets you edit them, and copies the commands that write the files.

## Requirements and cost

- macOS or Linux, Python 3.10+, and Git. No packages to install.
- Claude Code, signed in. Every session uses the login the `claude` command already has, such as a Claude subscription.
- Codex, signed in, for the four Codex reviewers. Without it, or when a Codex session fails, those reviewers run on Claude and the page says so.
- The GitHub CLI, signed in, for `--pr`.

A full run starts nine sessions (eight reviewers and the synthesis), each limited to 20 minutes; a run of the whole panel on a small pull request took about eight minutes. Reviewers read a snapshot of your branch, including uncommitted and new files, so you can keep working meanwhile. Claude reviewers can only read and search files (no shell, project settings, hooks, or MCP servers), and Codex reviewers run in Codex's read-only sandbox. Results stay in `.git/review-panel/` in the reviewed repository; nothing is posted anywhere.

## Credits

The live page shows the Claude and OpenAI marks from Font Awesome Free 7.2.0 under CC BY 4.0; see [references/icon-attribution.md](references/icon-attribution.md). The architecture reviewer's focus draws on John Ousterhout's *A Philosophy of Software Design*.

## What it does not do

The panel reviews and reports. It doesn't fix findings, post comments on pull requests, or run the project's tests. To get findings fixed, open one and choose **Copy fix prompt**, or tick several and choose **Prepare handoff**: either way you get a prompt to paste into the agent that will make the fixes, ending with the command that runs the panel again on the reviewers that raised them.
