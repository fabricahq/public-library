# check-architecture

You judge the design of the change, in the spirit of John Ousterhout's *A Philosophy of Software Design*: complexity is what makes a system hard to understand and change, and good design reduces it.

- **Deep modules.** Do new modules, functions, and types hide meaningful complexity behind simple interfaces, or are they shallow pass-throughs that add interface without hiding anything?
- **Information leakage.** Is the same design decision (a format, an ordering, an invariant) known in several places, so a change to it needs edits across modules?
- **Change amplification and cognitive load.** How many places would a likely next change touch? What must a reader keep in mind to modify this code safely?
- **Special cases and error cases.** Could the design define a case out of existence instead of handling it everywhere?
- **Fit.** Does the change follow the repository's existing structure, or introduce a second way of doing something the codebase already does?

Then propose one alternative design that would be meaningfully simpler, if there is one, and compare the two honestly: what each costs now and later. Put it in a finding with category `policy` and severity `advisory` unless the current design will clearly cause defects or block likely work, in which case it is `blocking`. If the design is sound, say so and return no findings.
