---
name: build
description: "Build one planned slice of work while the person who planned it is away: settle the done condition, decide reversible calls yourself, work in small verified units, prove the result on the real app, and hand back a decision log. Use when asked to build, implement, or carry out a planned feature, improvement, or bug fix, or to work through a plan without check-ins."
metadata:
  trailguide-skill-type: playbook
  trailguide-rules-used: |
    practices/code-design/record-facts-when-they-happen
    practices/testing/run-focused-tests-while-iterating
    practices/testing/test-bug-fixes-before-fixing
    practices/testing/test-observable-behavior
  trailguide-skills-used: |
    pstack:pstack/skills/principle-attack-the-premise
    pstack:pstack/skills/principle-build-the-lever
    pstack:pstack/skills/principle-fix-root-causes
    pstack:pstack/skills/principle-guard-the-context-window
    pstack:pstack/skills/principle-laziness-protocol
    pstack:pstack/skills/principle-never-block-on-the-human
    pstack:pstack/skills/principle-prove-it-works
    pstack:pstack/skills/principle-sequence-verifiable-units
    skills/show-me-your-work
---

# Build

You're building one slice of planned work, and the person who planned it isn't watching. When they come back, they'll check two things: that it works the way they wanted, and that any decision the plan didn't cover matches their judgment. Every step below serves that hand-back, so they shouldn't need to answer a question or read every line to trust the result.

Each step names the skill or rule it applies. The skills sit beside this one, at `../<name>/SKILL.md`; read each in full before the step that uses it. The project's own rules still apply throughout.

## Before you write code

1. **Find the plan and name the slice.** Read the plan, spec, issue, or task you were given. Name what this slice delivers and what it leaves out.
2. **Write the done condition as a check you can run.** For example, the tests for the new behavior pass and the flow works on the running app. Decide how you'll verify before you build: when the project has a skill for driving its app, use it.
3. **Start a decision log** with the `show-me-your-work` skill.

## While you build

4. **Work in small units that each end verified**, per `principle-sequence-verifiable-units`. Build a unit, check it, commit it, then start the next.
5. **For a bug, write the failing test first**, per the `practices/testing/test-bug-fixes-before-fixing` rule. Assert what users of the code can observe, per `practices/testing/test-observable-behavior`.
6. **Run the focused tests while you iterate**, per `practices/testing/run-focused-tests-while-iterating`, and the full suite before you hand back.
7. **Decide reversible calls yourself**, per `principle-never-block-on-the-human`, and log each one. Stop and wait only before an action no one can undo, such as a deploy, deleting data, a force-push to a shared branch, or a message sent outside the project.
8. **Fix causes, not symptoms**, per `principle-fix-root-causes`. After two fixes that share a premise fail, test the premise, per `principle-attack-the-premise`.
9. **Keep the change small**, per `principle-laziness-protocol`. When a check would take repeated manual work, build the script that does it, per `principle-build-the-lever`.
10. **Keep bulk output out of your context**, per `principle-guard-the-context-window`, so a long run still has room to finish.

## Before you hand back

11. **Prove it works on the real artifact**, per `principle-prove-it-works`. Run the done condition from step 2. A result that's inconclusive, or a check on the wrong surface, isn't a pass.
12. **Check the checks.** For each test you added, ask whether it would fail if the code were plausibly wrong. Fix any that wouldn't.
13. **Audit the decision log and get it reviewed**, as `show-me-your-work` describes. When your harness can't start a reviewer, hand back with the review outstanding, as that skill says, instead of waiting for one.
14. **Hand back.** Say what you built, the done condition's result with its evidence, and each decision the plan didn't settle, so the person can check it against their judgment. End with the Attention section from `show-me-your-work`. Leave the work committed on its own branch, ready to validate.

## When review findings come back

Use these steps whenever a reviewer returns findings on the slice, whether from the review in step 13 or a code reviewer on the pull request. Give each reviewer the plan or spec the slice follows and the decisions settled so far, and ask it to say which findings break them and which propose a policy they leave open.

15. **Classify each finding before you change anything.** It is one of three kinds:
    - **A defect against agreed behavior**, where the plan, spec, or acceptance criteria say what should happen and the code doesn't. Fix it at its cause and verify the fix, as steps 5 and 8 say.
    - **An unspecified policy choice**, where nothing agreed says what should happen and the finding proposes an answer. Don't choose it. Hand it back as step 14 says, as a decision for the person who owns the design, with the scenario, the options, your recommendation, and what each option means. Keep working on the rest of the findings while you wait.
    - **An optional improvement.** Take it only when it is small and inside the slice.
16. **Stop patching at a design checkpoint**, per `principle-attack-the-premise`. A checkpoint is reached when any of these happens:
    - a second finding lands on the same mechanism, or a finding lands in code the previous fix added;
    - a fix changes what a term the mechanism depends on means;
    - the slice gains persistence, a migration, or a new restriction on what a person can do that its plan didn't name.

    These signals make it likely that the design left a question open or has a flaw, and that each fix has been guessing at the answer. Before the next patch, write down the mechanism's contract where the slice's plan lives: what obligation it tracks, what settles that obligation, which failures leave it open, and what a person can do meanwhile. Check each finding so far against the contract. Hand back any open question the contract raises, as step 15 does for a policy choice, and resume once the answer is written down. After the contract changes the design, ask for a review of the whole slice rather than of the latest fix. A mechanism that infers what happened earlier from history is a common flaw here, and so is a migration that reconstructs facts old records lack; see `practices/code-design/record-facts-when-they-happen`.
17. **Turn a finding outside the slice's acceptance criteria into a follow-up ticket, not more scope**, per `principle-laziness-protocol`, and log it with `show-me-your-work`. The exception is a defect the slice itself introduced: fix that here.
18. **After two review rounds from one reviewer, hand the call back.** Don't start a third round on your own. Hand back as step 14 says, list the open findings in the Attention section from `show-me-your-work`, and ask the person who planned the slice whether to keep iterating.
