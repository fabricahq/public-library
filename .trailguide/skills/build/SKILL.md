---
name: build
description: "Build one planned slice of work while the person who planned it is away: settle the done condition, decide reversible calls yourself, work in small verified units, prove the result on the real app, and hand back a decision log. Use when asked to build, implement, or carry out a planned feature, improvement, or bug fix, or to work through a plan without check-ins."
metadata:
  trailguide-skill-type: playbook
  trailguide-rules-used: |
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
2. **Write the done condition as a check you can run.** For example, the tests for the new behavior pass and the flow works on the running app. Decide how you'll verify before you build:
   - **When the project has a verification skill** for driving its app, such as one `create-verification-skill` generated, update its feature map before you build. For each behavior this slice adds or changes that a user sees, write the journey a user takes through it, with the exact output each step must show. Cover the ways it goes wrong or comes back: a failure and its recovery, an undo, a change made by hand outside the app, a run with nothing to do. Those journeys are your done condition.
   - **When it has none**, use the project's tests and the running app, and in the hand-back suggest running `create-verification-skill` as its own task. Don't stop to build one.
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

11. **Prove it works on the real artifact**, per `principle-prove-it-works`. Run the done condition from step 2: drive every step of each journey on the built app and compare its output exactly. A result that's inconclusive, or a check on the wrong surface, isn't a pass. If the feature map was wrong about behavior this slice didn't touch, fix only what the slice needs, and in the hand-back suggest running `maintain-verification-skill`.
12. **Check the checks.** For each test you added, ask whether it would fail if the code were plausibly wrong. Fix any that wouldn't.
13. **Audit the decision log and get it reviewed**, as `show-me-your-work` describes. When your harness can't start a reviewer, hand back with the review outstanding, as that skill says, instead of waiting for one.
14. **Hand back.** Say what you built, the done condition's result with its evidence, and each decision the plan didn't settle, so the person can check it against their judgment. End with the Attention section from `show-me-your-work`. Leave the work committed on its own branch, ready to validate.
