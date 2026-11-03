---
name: create-verification-skill
description: "Generate a project-local verification skill that drives your app the way a user does - any language, framework, or platform. Use for /create-verification-skill, \"make a control skill for this repo\", or when a project has no way for an agent to drive the app and prove UI/CLI/service behavior."
disable-model-invocation: true
metadata:
  trailguide-skill-type: playbook
---

# Create a verification skill

Every serious project needs a way for an agent to use the real app and prove behavior: launch it, work through a feature the way a user would, and capture evidence. This skill generates that as a project-local skill named `verify-<app>`, tailored to the repo, with a small `control-<app>` CLI as the agent's hands and eyes. The agent drives the CLI one command at a time and picks each next step from what the last one showed; nothing in the skill replays a fixed script. Scripted, repeatable checks belong in the project's automated tests. You write the generator's output for the next agent, not for a human: it will be read cold, mid-task, by an agent that has never seen the app.

## 1. Interview the repo, not the user

Answer these from the codebase and only ask the user what you cannot observe:

- **Surface:** what does a user actually touch? A web UI, a CLI/TUI, a desktop app, an API, a mobile app, a library? A repo can have several; pick the primary one and note the rest.
- **Run:** how does the app start locally? Prefer the repo's own documented dev command (package scripts, Makefile, README quickstart). Note ports, env vars, seed data, auth.
- **Drive:** what can control the app and read its state? A browser automation library over the Chrome DevTools Protocol (Playwright, Puppeteer) for web and Electron, a debug port, a tmux/PTY harness for CLI/TUI, plain HTTP for services. Reuse what the repo already depends on. Existing e2e specs, expect scripts, and fixtures show stable selectors, setup, and seed data; read them for that, but don't make them the proof: a spec replays steps a human wrote once, and the proof is an agent using the app.
- **Observe:** what evidence can be captured? Screenshots, terminal transcripts, response bodies, logs, exit codes, DB state.
- **Isolate:** can two instances run side by side (ports, data dirs, profiles)? If not, say so in the generated skill: refusing to double-drive a shared instance beats corrupting the user's session.

If the checkout doesn't build or start as-is, fix that first (or report it precisely) before generating; a skill written against a broken base teaches wrong steps. When an irrelevant missing asset blocks startup (a static dir the API never serves, a sample config), the generated skill may create it, clearly marked as verification scaffolding, and remove it in cleanup.

## 2. Generate the skill

Choose the authored skill directory before writing. In a Trail Guide project, use `.trailguide/skills/local/verify-<app>/` (in a Trail Guide library, `.trailguide/skills/<library.name>/verify-<app>/`) and run `trailguide project sync` after authoring to install it into the configured agent targets. Otherwise, use the repository's documented project-local skill location, or the active agent's supported project-local location when the repository has none. Call the chosen folder `<skill-dir>` below. Inspect any existing skill there before changing it; never overwrite an installed or generated copy when an authored source owns it.

Write `<skill-dir>/SKILL.md` with YAML frontmatter (`name: verify-<app>` and a `description` that names the app, the surface, and when to reach for it - without frontmatter the skill never registers) and these sections, each grounded in what the interview actually found (no placeholders left):

- **Launch:** the exact command that starts the app for verification, and how to tell it's ready (a log line, a prompt). Launch must reach a usable state from an empty data dir, including any migrations and seed data. Ready means usable, not just that a process answers. A database health check can pass while its init scripts are still running. Include teardown. For a short-lived CLI or TUI there is no server to keep alive: launch means build the binary (or install deps) once, then start each drive in its own isolated PTY or tmux session.
- **Doctor:** one read-only check that answers "is this instance worth driving?" - process up, right version/build, port owned by us, auth valid. An agent runs this first whenever anything looks off.
- **Drive:** the `control-<app>` commands for reading and acting on the app, with real selectors from this repo, not examples, and how to decide each next step: read the state, act, wait on what the user would see, read again. Prefer stable handles (roles and accessible names, ARIA labels, data attributes, prompt strings, route paths) over coordinates and tab order.
- **Evidence:** what to capture for a proof and where it goes. State the proof standards: exercise the real user path, not internal setters or test-only endpoints; capture the action and the resulting state, not just the final screen; verify side effects (files written, rows inserted, messages sent) alongside what's visible; mocks only where a production boundary already isolates the external system; judge each step by what a user should be able to tell and the observable end state that proves it, never by comparing output verbatim: exact text that users or scripts rely on (machine-readable output, exit codes, errors that get parsed) belongs in the project's automated tests, which the feature file names, so it is checked on every commit rather than only when an agent drives a journey. A proof reads what the user saw as that user would, judging only from the captured output and the user's task, not filling gaps with what you know of the implementation: is anything missing, repeated, contradictory, or in the app's internal terms, and is it clear what happens next? Report what you find with the evidence; the right end state on confusing output isn't a pass, and output a script would notice changing calls for a test, not a pinned line. When the safe path is a dry-run or test mode, verify what it actually skips by observing (files, network, git refs) rather than trusting its name: some dry-runs still touch the network or open a browser.
- **Cleanup:** how to tear down instances the run created. Never kill by process name; kill what you started. Cleanup removes instances and scratch state, never the evidence: proof artifacts survive the teardown, in a location the skill names.
- **Helpers:** any script the skill ships is executable and its invocation is shown in the skill body. A helper the reader has to reverse-engineer is not a helper.

Build `control-<app>` as part of the skill, in the repository's own language and tooling, with tests for its parsing and error paths. Its commands cover the stack (`up`, `doctor`, `down`), reading state (a snapshot of the accessibility tree or screen, logs, network, screenshots), and acting (navigate, click, type, press, wait), with an escape hatch to the platform's raw debugging protocol for traces and profiles. Design it for an agent caller:

- One command does one user action or one read, and the app session persists between commands, so state, logs, and recordings carry across them.
- Subcommands group related commands, so `--help` discloses them gradually; every command has `--help` with an example.
- Output is machine-readable, such as one JSON object per command.
- A failure says what went wrong and what to do instead, such as the closest matching element names when a target matches nothing.
- Commands with destructive side effects have `--dry-run`.
- Every command that changes the app captures evidence on its own, so a proof never depends on the agent remembering to.

## 3. Seed the feature map

Create `<skill-dir>/features/README.md` plus one file per user-facing feature you can identify (aim for the top 3-5 to start, from routes, commands, menus, or docs). Follow the shape in [`references/feature-map-example/`](references/feature-map-example/README.md), adapting its illustrative Notes app and commands to this repository, with a README index and one file per feature. Each file answers, from the user's point of view: what the feature is, how to reach it, which `control-<app>` commands reach it (hints for the agent, not a script to replay), what observable end state proves it works, what a user should be able to tell at each step, and which automated tests check the exact output that users or scripts rely on. The four H2s are `Sub-features`, `How to get to it (user POV)`, `Driving it with control-<app>`, and `Gotchas`. If the seed data lacks a precondition that a journey needs, the journey reports a failure and the reason goes in that feature's `Gotchas`. Never weaken the journey to make it pass. The map is the repo's maintained verification source; a proof that drives one convenient entry point is incomplete when the map lists others.

## 4. Prove the generated skill before handing it over

Run its own instructions end to end once: launch, doctor, drive ONE mapped feature (one is enough; the map exists so later runs can cover the rest), capture evidence, read it as the feature's user would from the evidence alone, clean up. After cleanup, confirm the evidence still exists at the named location - a cleanup that eats the proof fails this step. Fix what fails, and run the generated cleanup after every failed iteration too, so broken attempts don't strand processes and ports. A generated skill that was never executed is a draft, not a deliverable. If you proved it in a stand-in for the real target (a container in place of a fresh VM, a local stack in place of a remote one), list every setup step the stand-in did that the target will not. Those steps stay unverified until a run on the real target covers them.

## 5. Offer the maintenance loop

Offer `maintain-verification-skill` as a separate follow-up for keeping the map honest as the app changes. It is not run during creation and is not required to complete this skill. If it is not installed, direct the user to select it from this library. Suggest a cadence only if they ask.
