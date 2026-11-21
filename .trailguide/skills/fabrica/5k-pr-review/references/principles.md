# Design principles

From John Ousterhout, *A Philosophy of Software Design*, 2nd edition: the book's own summary of its design principles and red flags. Page numbers point to the book. Rate a pull request's design against each, citing evidence from the PR.

## Principles

| # | Principle | Page | What to look for in a PR |
|---|-----------|------|---------------------------|
| 1 | Complexity is incremental: sweat the small stuff | 11 | Size and spread of the change; whether small inconsistencies were left behind. |
| 2 | Working code isn't enough | 14 | Strategic fixes over tactical patches; renames done whole; root causes fixed. |
| 3 | Make continual small investments to improve system design | 15 | Improvements made where others benefit, not only for this feature. |
| 4 | Modules should be deep | 23 | New interfaces much simpler than what they hide. |
| 5 | Design interfaces so the most common usage is as simple as possible | 27 | The everyday call or control is one step. |
| 6 | A simple interface matters more than a simple implementation | 61, 74 | Hard work done inside so callers stay simple. |
| 7 | General-purpose modules are deeper | 39 | Pieces built for more than one caller. |
| 8 | Separate general-purpose and special-purpose code | 45, 68 | Special cases kept out of general modules. |
| 9 | Different layers should have different abstractions | 51 | Each layer speaks its own vocabulary; few pass-throughs. |
| 10 | Pull complexity downward | 61 | Callers spared work the module can do. |
| 11 | Define errors out of existence | 81 | Operations that make would-be errors into no-ops or normal cases. |
| 12 | Design it twice | 91 | Alternatives considered and recorded. |
| 13 | Comments should describe things that aren't obvious from the code | 101 | Comments give intent and reasons, not restatements. |
| 14 | Design software for ease of reading, not ease of writing | 151 | Names and structure a reader understands without the history. |
| 15 | The increments of development should be abstractions, not features | 156 | Whether the PR grew abstractions or stacked features. |
| 16 | Separate what matters from what doesn't, and emphasize what matters | 171 | Important things prominent in code, data and UI; minor things quiet. |

## Red flags

| Red flag | Page | Symptom |
|----------|------|---------|
| Shallow module | 25, 110 | The interface isn't much simpler than the implementation. |
| Information leakage | 31 | One design decision is reflected in several modules. |
| Temporal decomposition | 32 | Structure follows the order operations run, not information hiding. |
| Overexposure | 36 | Callers must know rarely used features to use common ones. |
| Pass-through method | 52 | A method mostly forwards to one with a similar signature. |
| Repetition | 68 | A nontrivial piece of code repeated. |
| Special-general mixture | 71 | Special-purpose code not separated from general-purpose code. |
| Conjoined methods | 75 | One method can't be understood without the other. |
| Comment repeats code | 104 | The comment says only what the code next to it says. |
| Implementation documentation contaminates interface | 114 | An interface comment describes implementation details. |
| Vague name | 123 | A name too imprecise to carry information. |
| Hard to pick name | 125 | No precise, intuitive name fits. |
| Hard to describe | 133 | Complete documentation must be long. |
| Nonobvious code | 150 | Behavior or meaning can't be understood easily. |
