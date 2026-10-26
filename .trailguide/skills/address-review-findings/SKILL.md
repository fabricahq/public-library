---
name: address-review-findings
description: "Respond to review findings on work already built: sort each finding into a defect to fix, a decision to hand back, or follow-up work, and stop patching when findings keep landing on one mechanism. Use when code review comments, PR review threads, a reviewer's or review agent's findings, or requested changes come back and you're asked to address, fix, or answer them."
metadata:
  trailguide-skill-type: playbook
  trailguide-rules-used: |
    practices/code-design/record-facts-when-they-happen
---

# Address review findings

A finding is one problem a reviewer raised about work that's already built: a comment on a pull request, an item in a review agent's report, or a change a person asked for. Your job is to make the work right, not to make the findings stop. Patching each finding where it lands can quiet a reviewer while the design underneath stays wrong, and every patch gives the next round new code to find problems in.

Before you start, find what the work was meant to do: the plan, spec, issue, or ticket it was built from. You judge each finding against that, not against the reviewer's preference or your own.

## For each finding

1. **Decide what kind of finding it is before you change anything.**
   - **A defect:** what was agreed says what should happen, and the code doesn't do it. Fix it at its cause, with a test that fails without the fix.
   - **A decision:** nothing agreed says what should happen, so any fix would be you choosing the behavior. Hand it back to the person who owns the design, with the situation, the options, and your recommendation. Don't pick one and patch it in.
   - **Out of scope:** a real problem this work didn't cause. Record it as a follow-up ticket instead of growing the change.
   - **Not a problem:** answer the reviewer with the reason, citing what was agreed.
2. **Answer the reviewer** on each finding: what you changed, what you handed back, or why you changed nothing.

## When findings repeat

Stop patching when either of these happens:

- A second finding lands on the same mechanism.
- A finding lands on code that your last fix wrote.

Either one means the design is probably missing an answer. The fixes so far have each chosen one, and the reviewer keeps finding cases those choices don't cover. Before you change more code:

1. Write down what the mechanism must guarantee, in a few sentences: what it records, what it promises its callers, and what it does in each case the findings raised.
2. Check every finding so far against that statement. Fix the code to match it as one change, not one finding at a time.
3. If writing it down leaves a question that nothing agreed answers, hand that question back as a decision, and wait for the answer before building on it.

A common cause is a mechanism that works out what happened in the past from history, such as timestamps, the order of records, or which records exist. See `practices/code-design/record-facts-when-they-happen`.

## When rounds repeat

After two rounds of findings from one reviewer, ask the person who owns the work whether to keep going, instead of starting a third round on your own. Say what each round found and whether the findings are shrinking.
