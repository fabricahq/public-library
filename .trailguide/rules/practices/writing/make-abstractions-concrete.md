---
title: "Make important abstractions concrete"
whenToRead: "Before drafting, editing, or reviewing prose that makes a claim or explains an idea, such as describing a benefit, the size of a problem, a tradeoff, or how something works. Not meant for code comments or docstrings."
impact: "MEDIUM"
impactDescription: "Claims without numbers, examples, or analogies are hard to check, picture, or remember, so readers discount or forget them."
tags: "writing, examples, analogies"
attribution:
  - url: https://www.ybrikman.com/blog/2019/10/20/lessons-learned-from-losing-50-lbs/
    description: "Distilled from Yevgeniy Brikman's writing; the rotisserie chicken comparison comes from this post."
  - url: https://www.ybrikman.com/blog/2026/08/01/what-you-cant-vibe-code/
    description: "The iceberg analogy for mature software is adapted from this post."
  - url: https://www.ybrikman.com/blog/2018/08/12/the-10-to-1-rule-of-writing-and-programming/
    description: "Shows how counting additions and deletions makes rewriting effort concrete; the example below uses illustrative figures."
---

## Make important abstractions concrete

Give the reader something they can picture or inspect for each important unfamiliar idea. Choose a form that suits the explanation:

- **A specific number:** "loads in 300 ms," not "loads fast."
- **A real example:** a named case, a story, or a sample the reader can inspect.
- **An analogy to something familiar:** an object, place, or experience the reader already knows.
- **A useful visual or worked example:** a diagram, screenshot, table, or calculation that reveals a relationship. Explain what the reader should notice.

For factual claims, supply evidence appropriate to the claim: a source, a measurement with its conditions, or reasoning the reader can follow. An analogy explains an idea; it does not establish that a claim is true. A single example can show that something happens, but not how often it happens.

When a raw number won't land, convert it into something familiar. Yevgeniy Brikman doesn't say 50 pounds is a lot of weight. He says it's 17 Costco rotisserie chickens tucked under your shirt.

### Exceptions

- Use measured or sourced numbers for reported results. Label estimates with their assumptions and hypothetical examples as illustrative. When evidence is missing, narrow the claim or identify the gap instead of supplying a convincing-looking number.
- Not every sentence needs a number. Transitions and conclusions can restate a point abstractly once the piece has made it concrete.
- An analogy has to match the mechanism you're explaining. If it breaks somewhere the reader might push on, say where.

### Rationale

Abstract claims such as "significantly faster" leave readers unsure what changed. Concrete details make an idea easier to understand and remember; evidence lets readers judge whether to believe it. Keep those jobs distinct so vivid writing does not overstate what the author knows.

### Examples

#### Application: stating a benefit

**Incorrect (counterexample):**

> Our new cache dramatically improves dashboard performance.

"Dramatically" asks the reader to trust you. They can't picture it or check it.

**Correct:**

> With the new cache, the dashboard loads in 300 ms instead of 4 seconds.

The numbers here are illustrative. In a real piece, use measured values and say how you measured them.

#### Application: explaining an idea without data

**Incorrect (counterexample):**

> Mature software contains many hard-won lessons that aren't visible from the outside.

This is true but forgettable. The reader has no picture of what "hard-won lessons" means or how much of the software they make up.

**Correct:**

> Think of mature software as an iceberg. The interface sits above the water; crash recovery, edge cases, and security fixes sit below it. Copying the interface does not show that you've reproduced those protections.

This adapts Brikman's analogy without turning its proportions into software measurements. The image explains hidden complexity; a claim about a particular product's reliability still needs evidence.

#### Application: showing scale

**Incorrect (counterexample):**

> Writing a book involves a lot of rewriting.

**Correct:**

> I added 30,000 lines and deleted 25,000 to finish a 5,000-line draft. For every line in the finished draft, I added or deleted 11 along the way.

The figures are illustrative. In a real piece, use the author's own edit history and explain what was counted. Additions plus deletions measure editing activity, not distinct lines written or a required rewrite ratio.

### Validation

- Find the central claims and unfamiliar ideas, including those without words such as "faster" or "better." Check that the reader can locate the supporting evidence or explanation nearby or through a clear link.
- Check that reported numbers have a source or measurement conditions, estimates state their assumptions, and hypothetical examples are labeled. Attribute someone else's results to them.
- Check that an illustration or isolated anecdote has not been used as proof of a general factual claim.
- Read each analogy and ask whether it explains the real mechanism. Check that the piece flags where the analogy breaks, if a reader could push on that point.
- A conclusion that restates an already-concrete point in general terms is not a violation.
