---
title: "Make the actor and action clear"
whenToRead: "Before drafting, editing, or reviewing sentences in published prose, such as blog posts, announcements, or page copy, especially sentences that describe what a person, team, or product does. Not meant for code comments or docstrings."
impact: "MEDIUM"
impactDescription: "Sentences that bury the actor or the action in nouns and passive voice make readers reread or skim past the point."
tags: "writing, voice, verbs"
attribution:
  - url: https://steve-yegge.blogspot.com/2006/03/execution-in-kingdom-of-nouns.html
    description: "Steve Yegge's \"kingdom of nouns\" metaphor, applied here to prose instead of code."
  - url: https://www.ybrikman.com/blog/2014/07/11/on-writing-well/
    description: "William Zinsser's advice on active verbs and concrete subjects, quoted in Yevgeniy Brikman's review of On Writing Well."
---

## Make the actor and action clear

When a sentence describes an action, make clear who or what performs it. Prefer a concrete subject and a direct verb: a team ships, a reader chooses, a tool checks. Turn a noun back into a verb when that reveals the action. Prefer active voice when naming the actor helps the reader understand what happened.

Steve Yegge called code where nouns rule and verbs only tag along the "kingdom of nouns." Prose has the same problem. Readers can picture a team shipping a fix. They can't picture "the implementation of a remediation."

### Exceptions

- Keep the passive voice when the actor is unknown or doesn't matter and the thing acted on is the topic, as in "The repo was archived in 2019."
- Keep a noun when it names a real thing rather than a disguised action. "The deployment" is fine when it means a specific running system. "Performing a deployment of the app" is a disguised verb.
- Definitions and descriptions need no invented actor. "A rule is a versioned Markdown file" is clear as written. Noun endings alone do not establish a problem.
- Leave product names, quoted text, and established terms such as "infrastructure as code" unchanged.

### Rationale

Noun-heavy and passive sentences hide who does what. The reader has to rebuild the actor and the action before they can follow the point, so they reread or skim past it. Active verbs also make sentences shorter, because filler verbs such as "perform," "conduct," "provide," and "enable" drop out.

### Examples

These examples illustrate sentence construction. Use first-person accounts and product claims only when the author or project evidence supports them.

#### Application: announcing a feature

**Incorrect (counterexample):**

> The introduction of rule versioning enables the facilitation of safer updates for consumers of shared libraries.

Nobody acts in this sentence. Three nouns (introduction, facilitation, consumers) carry the meaning, so the reader has to work out who updates what.

**Correct:**

> Each rule now has its own version, so you can choose which rule updates to adopt.

"You" are the actor, "choose" is the action, and the sentence is shorter.

#### Application: telling what happened

**Incorrect (counterexample):**

> A decision was made to pause the plan visualizer, and focus was shifted to code quality.

The passive voice erases the author from their own story. The reader can't tell who decided or why it matters.

**Correct:**

> I paused the plan visualizer and switched to the code quality problem.

#### Application: a valid passive sentence

> The 2019 release was deprecated after the security audit.

This needs no change. The release is the topic, and the reader doesn't need to know which person deprecated it.

### Validation

- For each sentence describing an action, ask "who does what?" Check that the answer is clear, applying the passive-voice exception when the actor is irrelevant.
- Search the draft for likely passive constructions and noun-heavy phrases, for example `rg -n '\b(is|are|was|were|be|been|being) [a-z]+ed\b|\b(perform|conduct|provide|enable|facilitate)[a-z]* (an? |the )?[a-z]+(tion|ment|ance|ence|ity)\b' post.md`. Each match is a candidate, not a violation. Apply the exceptions before rewriting it. The pattern only finds regular "-ed" verbs, so read for irregular passives such as "was made" or "were taken" too.
- A sentence with a clear actor that uses one abstract noun is not a violation. Flag only sentences where the actor is missing or the action is buried.
