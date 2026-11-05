---
title: "Build the explanation in steps"
whenToRead: "Before drafting, editing, or reviewing prose that teaches an unfamiliar concept, explains how something works, or leads readers through a technical argument. Not meant for code comments or docstrings."
impact: "MEDIUM"
impactDescription: "Readers lose the argument when a conclusion depends on terms or reasoning the piece has not explained."
tags: "writing, explanation, reasoning"
attribution:
  - url: https://www.ybrikman.com/blog/2014/05/19/dont-learn-to-code-learn-to-think/
    description: "Separates computer science from programming, explains each, and then uses that distinction to reconsider the opening debate."
  - url: https://www.ybrikman.com/blog/2018/08/12/the-10-to-1-rule-of-writing-and-programming/
    description: "Walks readers from a question through inspectable measurements and comparisons before drawing a conclusion."
---

## Build the explanation in steps

Start from what the intended reader already knows and supply each premise before relying on it. For an unfamiliar mechanism, walk through a concrete case, explain why the result follows, and then state the broader lesson. Define a term when the reader first needs it; carry the same example forward when it helps them follow the chain.

A roadmap tells the reader where the piece is going. This rule governs the reasoning inside that route: each conclusion must follow from something the reader has already been shown or can reasonably be expected to know.

### Exceptions

- Write for the stated audience. Experienced readers do not need a tutorial on concepts they already use.
- A short announcement can link to an explanation instead of including it, provided its central claim is understandable on its own.
- Presenting the answer first is fine. The explanation that follows must still supply the steps needed to understand it.

### Rationale

A concrete example is useful only if the reader can connect it to the point. Brikman's explanatory essays introduce distinctions and work through their consequences before asking readers to accept a general lesson. Showing that reasoning lets readers test the argument and apply it elsewhere.

### Examples

#### Application: explaining a technical failure

**Incorrect (counterexample):**

> Retrying the webhook can double-count an event. Use idempotency to prevent that.

For a reader unfamiliar with webhook delivery, this names the problem and solution but skips how either works.

**Correct:**

> Suppose a service records an order, but its reply never reaches the sender. The sender cannot tell whether the order was recorded, so it sends the event again. If the service records every delivery as a new order, it counts the same purchase twice. Record the event ID with the order in one transaction, and enforce uniqueness on that ID. A retry then finds the existing result instead of creating another order. That property, where repeating the operation has the same effect as doing it once, is called idempotency.

This hypothetical example moves from a lost reply through its consequence to the mechanism that prevents duplication. The new term names an idea the reader now understands.

#### Application: writing for specialists

An announcement aimed at engineers who maintain webhook handlers can say that the handler now deduplicates event IDs transactionally and link to the implementation. Repeating the introductory lesson would slow those readers down.

### Validation

- Identify the intended reader and the knowledge the explanation assumes.
- At each new term or conclusion, check that its prerequisites are already explained, linked where appropriate, or familiar to that audience.
- Follow the example from cause to consequence. Check that the prose explains why the result follows, rather than merely naming a pattern.
- Check that the broader lesson stays within what the example and supporting reasoning establish.
