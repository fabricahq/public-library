# Producing a design-tree artifact

Use a JSON snapshot as the common artifact, whether you prepare it before opening the canvas or during an interview. The [schema](../schemas/design-tree.schema.json) is its machine-readable contract; the publisher also checks references and dependency cycles. Run `validate --snapshot /absolute/path/design-tree.json` before handing it to another agent. `publish` and `render` validate the same contract. Use `schemaVersion: 1`; `revision` advances when the design is published or an answer is submitted, confirmed, or cleared. It is separate from the schema version.

The canvas presents this artifact. It does not research, generate alternatives, or call a model. The invoking agent does that work and publishes the result. Live `state.json.session` is the authoritative published snapshot; exported `session` contains the same design plus separately labeled drafts and pending replies. Read current state before updating a working snapshot. `answer` always holds the latest submitted response. Unfinished drafts and delivery receipts are separate from that answer. Application-owned `answerState` records revision facts outside this schema; preserve it through exports and never author or edit it.

## Draft the question first

Keep the question and agent recommendation understandable without supporting disclosures. Resolve facts necessary for an informed recommendation yourself. Research is part of the agent’s normal work, not a separate artifact field. Put useful findings and background in `notes`, or verified examples and their lessons in `precedents`. Distinguish checked facts from uncertainty.

Add supporting context only when it materially helps this decision. These are optional, not a checklist: omit a field or use an empty array when nothing useful belongs there. There are no minimum counts. Never invent content to populate the artifact.

- `assumptions`: uncertain premises that could change the decision. Each has a stable local `id` and `statement`. Do not present assumptions as verified facts. If one proves false, review affected answers and their dependents.
- `alternatives`: genuinely different, plausible choices worth comparing. Each has a stable local `id`, `title`, and `description`. Include a useful trade-off in the description when needed, without requiring one. Exploring alternatives does not change the user's answer.
- `precedents`: relevant examples or sources you have actually checked. Each has a `title`, optional HTTP(S) `url`, and `insight` explaining what it contributes to this decision. Include important limits of the comparison in the insight. A URL is not required for a verified project example, but omitting it is not permission to invent a source. Do not search for precedents solely to fill this field.

Link governing constraints through `constraintIds` when applicable. Record the user's direct response in `answer`, including any explanation they volunteer. A short answer is sufficient. Do not require a separate justification, trade-off, or revisit condition, and never invent the user's reasoning. Ask a follow-up only when an ambiguity changes the decision.

Preserve useful context when republishing or resuming an export; update it when the evidence changes instead of flattening it into `notes`. Notes hold additional context. The canvas reveals supporting context on demand. Structural validation is not a completeness check: a partial preparation artifact must not overwrite a live tree with missing decisions or constraints.

## Constrain the constraints

Store `constraints` once at the snapshot root. The canvas's **Constraints** document is a view of this array, available from Artifacts and from linked questions. It updates with the published tree and travels with the export, including standalone canvases. Do not create a second CONSTRAINTS.md mirror.

- Include only the most important cross-cutting limits. Seven is a ceiling, not a target. Every constraint is a requirement that the design must satisfy.
- Each constraint has a stable ID, one statement of at most 160 characters, and a reason of at most 240 characters. When the user gives no reason, cite the instruction as the basis (for example, "Required by the user"); do not invent their motivation. Order by importance. No nested lists or bundled unrelated clauses to evade the cap.
- Derive requirements from explicit user instructions or verified external limits. Record uncertain limits as assumptions until resolved.
- When an eighth candidate appears, compare it with the existing seven. Merge genuine duplicates or remove a superseded requirement with the user's agreement. Otherwise ask the user which requirement should be revised. Never silently drop a hard requirement; a conflicting requirement becomes a question in the tree before it becomes an accepted constraint. Preserve an eighth user-required candidate verbatim on that reconciliation question, including that it is required and not yet in the capped list; do not lose it merely because it has no constraint ID yet.
- Put local acceptance details on their question, not in this global list. Link governing IDs with `constraintIds`; changing a constraint requires reviewing affected answers and their transitive dependents.

See [the enriched example](../examples/design-context.json) for field shapes. Its decisions and evidence are illustrative, not instructions or answers to the current interview.
