# Grill Me UI

Explore a design with your agent on a local canvas. Answer questions individually, inspect recommendations and examples, and review the follow-up decisions your answers reveal. Replies are saved locally and delivered to your chosen agent; the canvas does not call a model API itself.

Install `skills/grill-me-ui` from this library through Trail Guide, then invoke `$grill-me-ui` in Codex or `/grill-me-ui` in Claude Code. [SKILL.md](SKILL.md) owns the interview workflow. It includes the essential grilling and domain-modeling instructions; separately installed versions of those skills are optional.

## Install with Trail Guide

From a project that does not already have a `fabrica` source:

```sh
trailguide project init --non-interactive
trailguide project add source fabrica \
  --repository https://github.com/fabricahq/public-library.git \
  --skills skills/grill-me-ui \
  --non-interactive
trailguide project sync
```

This selects only this skill from the latest library release, including its runtime files and notices. Projects that select `recommended` also receive it when they update to a release containing it. If your project already has a `fabrica` source, add `skills/grill-me-ui` to that source's `skills.include` list and run `trailguide project update`.

The default source follows published library releases. To try merged changes before their release, add `--ref main` to the source command; Trail Guide warns that this uses unreleased content. A PR branch can be selected with `--ref BRANCH` in the same way. Sync keeps the fetched revision; `trailguide project update` moves it forward.

## Try the canvas

Requires macOS or Linux, Python 3.10+, and a modern browser. The server uses POSIX file locking. From this skill directory:

```sh
python3 scripts/grill_ui.py publish --require-help --session-dir sessions/demo --snapshot examples/question-help.json --expected-revision 0
python3 scripts/grill_ui.py serve --session-dir sessions/demo --port 0
```

Open the tokenized localhost URL printed by the server. The example is not connected to an agent. To resume it, run only the second command. Keep session directories out of version control: they contain answers, local access tokens, and runtime bindings.

The live interview can deliver replies to the exact bound Codex chat when its shared queue is available. Otherwise, the active agent listens to a local inbox, or you copy replies into chat. Claude uses the inbox or copy/paste. A running server alone does not mean an agent is listening. [The session contract](references/session.md) owns binding, delivery, recovery, and standalone export.

## Verification and credits

The repository's Skill scripts workflow runs the bundled Python and Node checks and browser journeys in disposable sessions. Browser checks use Playwright; the canvas itself has no npm dependency or build step. Direct-delivery tests use mocked hosts and do not send prompts to real chats.

Fabrica contributes the canvas and transport around Matt Pocock's grilling and domain-modeling workflow. The design-tree approach draws on Fred Brooks' *The Design of Design*. See [provenance](references/session.md#provenance), [Matt Pocock's MIT notice](references/Matt-Pocock-MIT-LICENSE.txt), [the embedded font's OFL notice](references/JetBrainsMono-OFL.txt), and [agent icon attribution](references/icon-attribution.md).
