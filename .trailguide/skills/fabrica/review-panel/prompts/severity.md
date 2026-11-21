Judge two things for each finding, from the code rather than from how alarming the finding sounds. The panel works out the severity from them, so the same facts get the same severity whoever reviewed them.

**Impact**, if it happens:

- `severe`: data loss or corruption, a security or privacy breach, or a core flow that stops working.
- `significant`: a wrong result someone relies on, or a stated requirement that isn't met; people can recover from it.
- `minor`: degraded behavior with a workaround, such as slowness, a confusing message, or an error instead of the right result.
- `cosmetic`: polish or maintainability only, such as structure, naming, tests, or comments.

**Likelihood** that real use hits it:

- `common`: a normal path that people use routinely.
- `uncommon`: ordinary actions in a less common order or state, such as a second tab, a back button, or a retry.
- `rare`: needs unusual timing, a failure such as a dropped request, or several conditions at once.

For a security finding, likelihood is whether an attacker can trigger it, not whether a user would by accident: a hole someone can exploit on purpose is `common`. For docs, likelihood is how often people follow that part of the docs.

The severity follows from the two:

| Impact | Common | Uncommon | Rare |
|---|---|---|---|
| severe | critical | high | medium |
| significant | high | medium | low |
| minor | medium | low | low |
| cosmetic | low | low | low |

Critical and high block merging; medium is fine to merge with a follow-up; low is optional.

Give the reason in `severity_reason`: one sentence naming the impact and the likelihood, such as "Loses typed text, but only when a save fails and the person leaves within a second: severe but rare." When you are unsure the scenario happens, choose the lower likelihood. A `policy` finding takes the impact of its worst plausible outcome.
