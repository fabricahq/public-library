# Review Panel

Review a change with a panel of eight focused reviewers instead of one generalist. Each reviewer is a separate, read-only Claude Code or Codex session that checks one thing in depth. A synthesis session then reads the code behind every finding, merges the duplicates, drops the false positives, and hands you one ranked list plus the questions only you can answer. A local page shows each reviewer's status, what it's reading, its findings, and the synthesis as it lands.

| Reviewer | Checks | Runs on |
| --- | --- | --- |
| check-acceptance-criteria | Checks the change against the known acceptance criteria and product decisions | Claude Opus, high effort |
| check-correctness | Traces concrete inputs through the new logic to find wrong results | Codex, GPT-6.2 Astra, high effort |
| check-security | Checks trust boundaries, secrets, injection, and tenant isolation | Codex, GPT-6.2 Astra, high effort |
| check-rules | Checks the change against the repository's written rules: Trail Guide rules, AGENTS.md, CLAUDE.md, and style guides | Claude Opus |
| check-docs | Checks that the docs still match the code after this change | Claude Opus |
| check-supportability | Checks that failures surface, can be traced, and can be recovered | Codex, GPT-6.2 Sol, high effort |
| check-performance | Flags only bottlenecks too large for the change's real workload | Codex, GPT-6.2 Sol, high effort |
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
├── panel.yaml              which reviewers run, in what order, the synthesis model, walkthroughs, and retention
├── walkthroughs.md         how an agent starts the app and records it, for video walkthroughs
└── reviewers/
    ├── check-security.md   replaces or extends a built-in reviewer
    └── check-payments.md   adds a new reviewer
```

Each reviewer file is that reviewer's focus prompt in Markdown, with `summary`, `harness` (`claude-code` or `codex`), `model`, and `effort` in its front matter. A file named after a built-in reviewer replaces its prompt, adds to it with `mode: append`, or, with front matter only, keeps the built-in prompt and changes just its settings. Any other name adds a reviewer, which needs a `summary` and a prompt. `panel.yaml` is optional: its `reviewers` list picks and orders the panel, and its `synthesis` map sets the synthesis model. Without a list, every built-in reviewer runs, plus every file in `reviewers/`.

The panel reads this folder from the checkout it runs in, never from a pull request under review, so a change can't rewrite the panel that judges it. `--panel DIR` reads another folder for one run. To edit the folder in a page instead, run this in the repository:

```sh
python3 PATH_TO_SKILL/scripts/review_panel.py settings
```

It opens the latest run's page at its settings window, which shows where each reviewer's settings come from (built-in or the repository) and saves edits as files in `.fabrica/review-panel/`, uncommitted, for you to review and commit. A saved report page can't write files, so its settings window copies the commands that write them instead.

## Severity

Each reviewer rates a finding's impact if it happens (severe, significant, minor, or cosmetic) and how likely real use is to hit it (common, uncommon, or rare), with a one-line reason. The script works out the severity from the two with a fixed table, so the same facts get the same severity whichever reviewer rated them:

| Impact | Common | Uncommon | Rare |
|---|---|---|---|
| severe | critical | high | medium |
| significant | high | medium | low |
| minor | medium | low | low |
| cosmetic | low | low | low |

Critical and high findings block merging, so the verdict is `fix-first`; medium is fine to merge with a follow-up, and low is optional. [prompts/severity.md](prompts/severity.md) defines each rating for the sessions, and the page's Guide shows the same definitions.

On the page, **Archive** (or <kbd>E</kbd>) sets aside a finding you've chosen to leave as it is: it leaves the table and the handoff, and the **Archived** button lists what you've archived, where you can unarchive it. The live page saves the choice in the run's state; a saved report.html keeps it in your browser.

## Video walkthroughs

A repository can have the panel record a short video of each finding that blocks merging (critical or high), or of every finding, so a person can see what it looks like in the running app and judge how much it matters. After the synthesis, an agent runs the change in the run's temporary worktree, follows `walkthroughs.md` to start the app and drive it in a browser with video on, and reports whether the problem reproduced, didn't, or can't be seen in the UI. Each video appears in a Walkthrough tab on its finding.

```yaml
# .fabrica/review-panel/panel.yaml
walkthroughs:
  record: blocking   # off (the default), blocking (critical and high findings), or all
```

`walkthroughs.md` says how to start the app on its own ports, when it's ready, how to sign in with test data, how to record (Playwright with `video: 'on'` is a good default), and how to stop everything. The Video walkthroughs page in Settings explains the setup and copies a prompt that has your coding agent do it. Unlike the reviewers, a walkthrough runs the change's code with a shell, so the panel never records a pull request from a fork unless you pass `--allow-run`. `--walkthroughs all` overrides the setting for one run. To add videos recorded some other way to a finished run's finding, use `review_panel.py attach RUN_DIR S1 video.mp4 --summary '...'`.

## Cleanup

Runs, videos included, live in `.git/review-panel/` and are never committed or pushed. Each time the panel starts, it deletes finished runs whose review is over: the pull request merged or closed, or the local branch merged into its base or deleted. It also deletes runs older than 14 days, which `retention: {days: N}` in `panel.yaml` changes. When GitHub can't be reached, a run is kept. `review_panel.py prune --dry-run` shows what it would delete, `prune` deletes it now, and `run --keep-runs` skips the cleanup once.

## Requirements and cost

- macOS or Linux, Python 3.10+, and Git. No packages to install.
- Claude Code, signed in. Every session uses the login the `claude` command already has, such as a Claude subscription.
- Codex, signed in, for the four Codex reviewers. Without it, or when a Codex session fails, those reviewers run on Claude and the page says so.
- The GitHub CLI, signed in, for `--pr`.

A full run starts nine sessions (eight reviewers and the synthesis), each limited to 20 minutes; a run of the whole panel on a small pull request took about eight minutes. Reviewers read a snapshot of your branch, including uncommitted and new files, so you can keep working meanwhile. Claude reviewers can only read and search files (no shell, project settings, hooks, or MCP servers), and Codex reviewers run in Codex's read-only sandbox. Results stay in `.git/review-panel/` in the reviewed repository until the review is over; nothing is posted anywhere.

## Credits

The live page shows the Claude and OpenAI marks from Font Awesome Free 7.2.0 under CC BY 4.0; see [references/icon-attribution.md](references/icon-attribution.md). The architecture reviewer's focus draws on John Ousterhout's *A Philosophy of Software Design*.

## What it does not do

The panel reviews and reports. It doesn't fix findings, post comments on pull requests, or run the project's tests. To get findings fixed, open one and choose **Copy fix prompt**, or tick several and choose **Prepare handoff**: either way you get a prompt to paste into the agent that will make the fixes, ending with the command that runs the panel again on the reviewers that raised them.
