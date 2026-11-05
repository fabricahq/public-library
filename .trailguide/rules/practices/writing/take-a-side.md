---
title: "Take a side and earn it"
whenToRead: "Before drafting, editing, or reviewing writing that argues for a position, recommends a choice, compares options, or asks readers to adopt something, including its thesis and conclusion. Not meant for code comments or docstrings."
impact: "MEDIUM"
impactDescription: "Hedged or one-sided arguments give readers nothing to act on and lose skeptical readers' trust."
tags: "writing, argument, persuasion"
attribution:
  - url: https://www.ybrikman.com/blog/2013/09/29/the-10x-developer-is-not-myth/
    description: "Distilled from Yevgeniy Brikman's treatment of objections and limits."
---

## Take a side and earn it

When a piece argues, recommends, or compares, commit to a position and back it:

1. **State the position plainly.** Make the recommendation clear before asking the reader to accept it. Remove hedges that add no information; retain uncertainty that changes how the reader should interpret the claim.
2. **Address the strongest relevant objection.** Present it fairly, then answer with evidence or explicit reasoning. If the objection stands, narrow or revise the recommendation.
3. **State the boundary.** Explain the conditions under which the recommendation holds and what would make another choice reasonable.

### Exceptions

- This rule doesn't apply to neutral reference docs or how-to steps that make no recommendation.
- Being bold means being clear, not claiming more than you know. If the evidence is thin, say so plainly and keep the claim narrow.
- Keep hedges that report real uncertainty, such as "I tested six models, so treat this as an early signal." Remove only hedges that soften the claim without adding information.
- An investigation can develop its position as evidence emerges. A short recommendation needs only the objection or limitation that could materially change the reader's decision, not an exhaustive debate.

### Rationale

Readers need both a recommendation and a reason to trust it. Answering a serious objection lets them judge the reasoning. Stating where the recommendation stops applying helps them use it in their own situation.

### Examples

#### Application: stating the thesis

**Incorrect (counterexample):**

> There may be some cases where skills could perhaps be less than ideal for delivering certain kinds of guidance.

Four hedges in one sentence. The reader can't tell what you believe.

**Correct:**

> I like skills and use them often. But they're a clumsy way to deliver agent guidance, for four reasons.

The first sentence concedes what's good about skills. The second states the position without hedging and promises the evidence.

#### Application: handling the obvious objection

**Incorrect (counterexample):**

A post that argues for agent rules and never mentions whether agents actually follow them. Every skeptical reader is thinking it, and the silence reads as avoidance.

**Correct:**

> Rules tell an agent what to do, but the agent can still ignore them. Use automated checks for requirements you can test, and review the rest before merging.

This illustrative recommendation acknowledges the limitation and explains how to account for it. Claims about measured compliance would also need the models, tasks, and results behind them.

### Validation

- Check that you can underline the recommendation and identify the reasoning supporting it. In an investigation, check that the conclusion follows from the evidence developed along the way.
- List the hedge words and check that each remaining one reports real uncertainty.
- Name the strongest relevant objection and check that the piece answers it with evidence or reasoning, or adjusts the recommendation.
- Check that the scope and decision-changing limitations are clear. Do not add a token concession just to satisfy a checklist.
- A neutral how-to or reference page with no recommendation is not a violation.
