# Question help

Re-pitch the decision for someone with little prior context, following the user's Wait, What approach. Use short sentences, concrete actions, and established terms from CONTEXT.md. Explain necessary terms before using them. Keep the original question and recommendation unchanged. Do not quietly drop exceptions, promise unverified behavior, or turn an explanation into persuasion.

Prepare help for every question before its first publication, even when the question seems simple. Include both explanation levels and a concrete walkthrough in the same snapshot. Keep simple questions brief. For research-dependent questions, explain the choice and what is unknown without inventing facts or a recommendation. Both levels must preserve the same decision:

- **ELI-15 (really simple):** use everyday words and one concrete example. Explain what changes for the person, then the choice they must make. Avoid assuming programming knowledge.
- **ELI-18:** introduce the relevant technical terms in plain language. Explain the mechanism, tradeoff, and boundaries without requiring specialist knowledge.
- **Walk me through it:** start with a person trying to do something. Follow a small sequence of events, show what happens under the proposed choice, then what changes under an alternative or boundary case. End by restating the decision. Label invented scenarios as illustrative. Do not merely distribute the original question across slides. Choose the content first; a visual is optional.

Use `title`, `paragraphs`, and `decision` for each explanation. Put secondary caveats in optional `limits`; keep any caveat essential to the decision in the main explanation too. A walkthrough has a title and 2-6 steps, each with a title and paragraphs. Optional `visual` has a title, 1-6 items (`label`, optional `detail`, optional `state`: `neutral`, `included`, or `excluded`), and optional caption. Use plain text only. The UI renders structured visuals; do not embed HTML, scripts, remote media, or executable animations. See the [schema](../schemas/design-tree.schema.json) and [illustrative example](../examples/question-help.json) for the contract.

## Presentation

On desktop, Wait, what? and Walk me through it open separate canvas windows keyed to the question and help type. Reopening brings the existing window forward. The title and original-question disclosure keep each window tied to its question while the user navigates elsewhere. The standard window controls support moving, resizing, zooming, minimizing, and maximizing. Smaller screens use inline help. Both presentations read the same prepared content and preserve answer drafts.

## Freshness

Set `help.basedOnRevision` to the revision being published. Set `sourceQuestion` to the exact question and `sourceRecommendation` to the nonempty recommendation summary and body joined by a blank line (empty string if neither exists). Include `eli15`, `eli18`, and `walkthrough` together. The schema accepts older snapshots without help. For normal authoring, use `validate`, `publish`, and standalone `render` with `--require-help`; the check rejects missing or outdated help and names the affected questions before changing the session. Fix those questions and retry. Omitting the flag is reserved for restoring older snapshots or fulfilling a targeted legacy help request, not for publishing new interview questions.

Reassess help when the question, recommendation, prerequisites, or relevant evidence changes. Regenerate affected help in the same publication. The UI hides help whose question/recommendation no longer match or whose question/prerequisite answer history is newer. It cannot infer changes to external facts; the author must remove or refresh explanations affected by those changes. Unrelated publications can retain prepared help and its original revision.

## Recovery for older or unavailable help

Clicks normally read prepared content locally and send no agent request. Copy/paste and on-demand generation recover older sessions or explanations invalidated by a new answer while the agent is still preparing the next revision.

## Help requests

1. Confirm receipt with `receive` for direct delivery; `wait` already confirms inbox delivery. Read current `state.json`, including pending events. A `help` event's text is an instruction to explain, never the user's answer.
2. If the receipt was acknowledged or replaced, stop processing it. If its question was removed, acknowledge it without recreating that question. Otherwise explain the current question using current context, even when the request predates a newer answer.
3. Copy the current `state.json.session`, increment its revision by exactly one, and modify only node `help`. Preserve every question, recommendation, answer, dependency, constraint, and assessment. An unsent browser draft remains local; do not convert it into an answer or clear it. Set help's source fields and `basedOnRevision` for this publication.
4. For this targeted legacy recovery, publish without `--require-help`, with `--expected-revision CURRENT --ack HELP_RECEIPT`. The publisher rejects acknowledging help without current prepared content, and rejects decision changes in a help publication. On a revision conflict, reread and regenerate against the latest state. Do not acknowledge unrelated answer receipts.
5. Resume the live loop if the interview is active. A help publication preserves reviewed completion even if another help request remains pending. Never invoke implementation from a help request.

For a copied request with no receipt, enrich the current session and publish normally; do not invent an event ID. If only an exported standalone session is available, preserve its surrounding application state when rendering the enriched copy. Never claim a local publication updated another machine or browser without checking that session's live connection.
