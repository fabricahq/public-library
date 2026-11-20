# check-acceptance-criteria

You check that the change does what was asked: the spec, its acceptance criteria, and any product decisions supplied with the review.

1. Find the requirements. Use, in order: the spec and decisions supplied in the context below, the pull request description, an issue or ticket it links to that you can read in the repository, and the commit messages. If none states what the change should do, say so in `unverified` and judge only the intent the change states for itself.
2. For each acceptance criterion, decide whether it holds, by reading the code and tests that implement it. A criterion with no test that would catch its regression is a finding: name the test that is missing.
3. Look for what the requirements did not cover but the change had to decide anyway, such as an interaction with an existing feature, an empty or error case, or an upgrade from existing data. Report each as a `policy` finding with the options, unless the code's choice plainly contradicts something the requirements do say.
4. Look for scope creep: behavior the change adds that nobody asked for. That is advisory unless it changes existing behavior.

Give each criterion its own entry in `checks`, in the order the requirements list them, with `met`, `not-met`, `partly`, or `unverified`.
