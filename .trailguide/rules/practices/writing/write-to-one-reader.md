---
title: "Write to one reader as if they're across the table"
whenToRead: "Before drafting, editing, or reviewing the tone of blog posts, announcements, newsletters, or other first-person writing, including openings, transitions, and conclusions. Not meant for code comments or docstrings."
impact: "LOW-MEDIUM"
impactDescription: "Impersonal, lecture-style prose loses readers' attention, so fewer of them reach the point."
tags: "writing, voice, tone"
attribution:
  - url: https://www.ybrikman.com/blog/2014/05/19/dont-learn-to-code-learn-to-think/
    description: "Distilled from Yevgeniy Brikman's conversational style, including direct address and reader questions."
---

## Write to one reader as if they're across the table

Write like you're explaining the idea to one person over coffee:

- Address the reader directly when it helps them connect the idea to their situation. Use "I" for the author's experience and "we" for a team's shared experience.
- Use familiar words and natural contractions. Explain technical terms the intended reader may not know.
- Anticipate the reader's questions. Ask one explicitly when it helps frame the explanation; a direct statement can work just as well.
- Tell first-person stories only when the author supplied or documented the experience. Attribute other people's stories to them; label invented scenarios as hypothetical.
- Let sentence length follow the thought: use room to explain, and a short sentence to emphasize a consequence. Keep humor and asides only when they fit the author's voice and carry the point.

### Exceptions

- This rule doesn't apply to reference documentation, legal text, UI labels, or error messages. Keep those neutral and precise.
- Don't fake enthusiasm. Use a reaction such as "Wow." or "Insane." only after something genuinely surprising, and use only a few in a piece.
- A question that opens an explanation may take a section to answer. Make progress toward the answer rather than leaving a string of unanswered prompts.
- Direct address, anecdotes, jokes, and exclamations are options, not quotas. Preserve the author's voice rather than borrowing another writer's catchphrases or persona.

### Rationale

Conversational writing reduces the distance between writer and reader. Its value comes from explaining at the reader's pace and taking their questions seriously. Adding reactions or first-person claims to every paragraph can sound rehearsed and can misrepresent the author's experience.

### Examples

#### Application: explaining a next step

**Incorrect (counterexample):**

> Evaluation of agent compliance with the team's rules should be performed prior to adoption.

The reader has to translate the formal wording into something they can do.

**Correct:**

> Try the rules on a task your team actually does. Read the agent's changes and note which instructions it missed before you adopt them.

This speaks directly to the reader and gives them a concrete next step without inventing a test result or the author's personal experience.

#### Application: moving between sections

**Incorrect (counterexample):**

> The following section describes the maintenance considerations associated with this approach.

**Correct:**

> That gets the tool running. Who fixes it when it breaks?

This illustrative transition moves from setup to maintenance through a question the next section answers. It does not require a joke or a stock conversational phrase.

#### Application: valid neutral text

A table of CLI flags or a page of terms of service stays neutral. This rule doesn't apply to it, so it needs no change.

### Validation

- Read the piece aloud. Flag sentences you'd never say to a colleague, such as "It is recommended that," "One should," or "Users are able to."
- Check that the piece meets its intended reader's knowledge level; an opening need not contain a particular pronoun.
- Check that substantive questions receive answers or an honest account of what remains unknown, in the passage or section they introduce.
- Verify that personal experiences and results belong to the named speaker. Clearly label hypothetical examples.
- Read transitions and asides aloud. Remove those that feel inserted to meet a tone checklist, and preserve useful variation in sentence length.
