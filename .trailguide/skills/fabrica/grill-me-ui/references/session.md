# Session contract

Requires Python 3.10+ and a modern browser. Uses the Python standard library; no API key, npm package, external script, or external service is required. The agent running this skill is the LLM. The server saves answers durably and either queues a prompt into a bound Codex session or exposes an inbox to an active agent. It does not call a model API itself.

## Snapshot

The snapshot is the shared design-tree artifact. [design-tree.md](design-tree.md) explains when agents add optional notes, assumptions, alternatives, and precedents, alongside up to seven constraints. [The JSON Schema](../schemas/design-tree.schema.json) defines the fields; `validate --snapshot FILE` checks them without publishing.

The structural example below is compatible with older sessions. For normal publication, also include prepared help for every node, as in [the complete example](../examples/question-help.json).

```json
{
  "id": "stable-session-id",
  "title": "The design we are exploring",
  "revision": 1,
  "nodes": [
    {
      "id": "Q1",
      "parentId": null,
      "title": "Core goal",
      "question": "What should this achieve?",
      "answer": null,
      "agentRecommendationSummary": "A quiet canvas.",
      "agentRecommendation": "Keep the design tree visible and show details only when a question is selected.",
      "dependsOn": [],
      "notes": "Optional additional context or document reference"
    }
  ]
}
```

One or more top-level elements (`parentId: null`), with no parent or dependency cycles. Do not invent a generic root to connect independent design elements. `parentId` names the one question this question sits beneath in the tree. It is also an implicit prerequisite, not just a visual grouping. `dependsOn` lists additional prerequisite questions, usually from other branches; do not repeat the parent there. For example, a search-interface question can have the search-strategy question as its parent and also depend on a separate privacy question. Both prerequisites must have current answers for the interface question to be ready. An answer is the latest submitted nonempty text, or null. The canvas derives answered, ready, waiting, and needs-review states; these are not authored schema fields. Keep nodes concise; use the detail panel for full question text. Preserve IDs and increase revision by exactly one on each publication. The UI supports up to 100 nodes.

Write `agentRecommendationSummary` as the shortest accurate answer, often "Yes." or "No." for a yes/no question. It appears in its own bold paragraph. Put supporting explanation in `agentRecommendation`, rendered separately in regular text without repeating the summary. Both are plain text. Submitting from the Recommendation tab records both paragraphs. Build on this copies them into the editable draft; only explicit submission makes the active choice the answer. Older snapshots without a summary still show their recommendation as regular text.

## Question help

Every newly authored node includes `help` with prepared ELI-15 and ELI-18 explanations and a scenario walkthrough. Follow [the authoring and event contract](question-help.md). The schema keeps this field optional for older snapshots. Normal publication uses `--require-help` to catch missing or stale content before the revision becomes visible. A `help` receipt travels through the same durable transport as answers but never changes an answer, review state, or completion. Publish current help with `--ack`; the publisher refuses changes to interview decisions in that operation. Prepared help opens immediately. Missing or stale help requests the agent; copy/paste remains available when automatic delivery is unavailable.

## Confidence assessments

Each node may include `contextConfidence` and `recommendationConfidence`. Each assessment contains `level` (`low`, `medium`, or `high`), a nonempty `reason`, and optional `evidence` containing a short quote or source reference. Omit an assessment when it has not been made; omit recommendation confidence when no recommendation exists. Older snapshots remain valid.

- **Context confidence** describes how clearly the supplied context establishes the user's intended decision. High means explicit and consistent; medium means partial or implied; low means missing, ambiguous, or conflicting.
- **Recommendation confidence** describes the strength of the proposed direction. High means strong reasons to prefer it; medium means plausible with meaningful tradeoffs; low means unresolved tradeoffs or missing information. It does not measure whether the user agrees.

For example, a clearly stated preference can have high context confidence while an uncertain implementation recommendation has low recommendation confidence. Neither rating is an answer, review state, or calibrated probability. Changing only an assessment does not invalidate a submitted answer. Refresh assessments when relevant evidence changes.

Tree and Matrix share independent multi-select filters: selected levels combine with OR within a dimension and AND across dimensions. Unassessed questions remain visible by default and occupy a separate list outside the matrix. Filtering dims excluded tree nodes to preserve their prerequisite context; selected questions and drafts remain accessible. Reset filters restores the full set. Confidence filtering never changes completion or answer validation.

## Answer and review state

Submitting an answer updates `session.nodes[].answer` immediately. Editing alone changes only the browser draft. Delivery acknowledgment means the agent processed a receipt; it does not confirm the user's decision.

Application-owned `answerState` lives beside `session` in `state.json`, never inside the design-tree schema. Per question, `changedAt` records the revision of its latest answer, question, prerequisite-link, or linked requirement change, and `confirmedAt` records the user's latest submission or confirmation. The UI compares these revision facts across prerequisite paths to derive Needs review. Unanswered questions have no review flag. Unchanged publications and delivery acknowledgments do not confirm answers.

**Keep this answer** confirms the existing text against current prerequisites. It does not change the answer or force dependents to reconsider unchanged text. Earlier questions must be reviewed first. **Clear answer** reopens the question and preserves dependent answers. Restoring a prior answer does not silently reconfirm its dependents.

Answers, revision facts, and receipts commit atomically in `state.json`. Receipts remain in `events` for retry and supersession checks. A stale edit cannot overwrite a newer answer or confirm against changed prerequisites. Its draft remains available; the user reviews the changes before resubmitting. Never edit `answerState` or replay a clear receipt as a new mutation.

## Commands

Resolve `SKILL_DIR` to the directory containing this skill. `SESSION_DIR` is a task-owned working directory. All commands emit JSON results. Quote paths.

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" publish --require-help --session-dir "$SESSION_DIR" --snapshot /absolute/path/next.json --expected-revision 0
python3 "$SKILL_DIR/scripts/grill_ui.py" serve --session-dir "$SESSION_DIR" --port 0
```

`serve` keeps a session-local URL token across restarts and prints a tokenized localhost URL and stays in the foreground. Retain its tool process handle. Open the exact returned URL. Use an available browser-open tool, or `open URL` on macOS. The token is a local capability; do not publish it. Only the tokenized UI and API are served, never a workspace directory.

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" wait --session-dir "$SESSION_DIR" --timeout 20
```

Keep calling `wait` while the interview is active, in a completion-aware foreground tool call whose yield window exceeds the wait. Receipt should immediately return control to the agent, without an intervening sleep or delayed process poll. It returns `event`, `timeout`, or `paused`; the full event is included. Before returning an event, `wait` records `receivedAt`. Events stay pending until acknowledged. `wait` renews a 75-second presence lease. The canvas can still queue a reply when the agent is offline and offers a copyable message.

After processing an answer, write the next JSON snapshot and publish it atomically with its receipt:

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" publish --require-help --session-dir "$SESSION_DIR" --snapshot /absolute/path/next.json --expected-revision 1 --ack EVENT_ID
```

A revision conflict refuses the update; read `state.json` and reconcile. An acknowledgment only means the agent processed the submission. The submitted answer is already current; processing does not remove a review indication. For a pause event, acknowledge it without inventing a design revision:

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" ack --session-dir "$SESSION_DIR" --event EVENT_ID
python3 "$SKILL_DIR/scripts/grill_ui.py" offline --session-dir "$SESSION_DIR"
```

The session directory holds `state.json`, optional `connection.json` and delivery receipts, and a short-lived presence file. `state.json.session` is the current design artifact; the surrounding application state owns revision history and durable events. Normal event consumption uses `wait`. One pending answer per question is allowed; updating it immediately replaces the current answer and supersedes its previous receipt. Unrelated pending answers must be preserved when publishing.

## Finishing the interview

An answered last question is still awaiting the agent's review. Once every branch is settled, publish the next snapshot with `--complete`, acknowledging the last processed receipt in the same operation:

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" publish --require-help --session-dir "$SESSION_DIR" --snapshot /absolute/path/final.json --expected-revision CURRENT_REVISION --ack EVENT_ID --complete
```

Omit `--ack` when no receipt remains. The publisher rejects completion if there are pending answer or pause receipts, unanswered questions, or dependent answers needing review. Help requests do not invalidate reviewed decisions. It records completion against that exact revision in application state, outside the authored design-tree schema. A new answer submission or decision publication reopens the interview unless the agent explicitly completes the new revision. Help requests and publications that only enrich help preserve reviewed completion. Stop waiting after completion, keep the canvas available, and let the user choose the next step in chat.

The toolbar agent status shows Waiting until receipt and a spinner with Reviewing while the agent processes answers, without shifting the canvas. The status strip is reserved for completion and actions the user needs to take. Only explicit completion offers **Copy spec prompt**, which includes the complete design and asks the agent to use `/tospec` to prepare specifications for review. This button copies text; it does not invoke a skill or send a message. Unfinished edits must be saved or discarded first. An older session without an explicit completion signal asks for a final review instead of claiming the interview is done.

## Live official artifacts

Register each canonical project document after it exists:

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" artifact --session-dir "$SESSION_DIR" --file /absolute/project/CONTEXT.md --title Glossary
python3 "$SKILL_DIR/scripts/grill_ui.py" artifact --session-dir "$SESSION_DIR" --file /absolute/project/docs/adr/0001-example.md --title "Decision: example"
```

The session's `artifacts.json` stores file references only. The server reads those exact files when the canvas receives a change notification, including changes made outside the interview. Do not create mirrors, extracted summaries, or separate viewer documents. The labeled Artifacts toolbar button opens a docked sidebar of registered files. Selecting one opens a file window on the canvas with a file icon and filename. Its **Copy file path** action copies the canonical absolute path. Rendered and Source switch between readable Markdown and syntax-highlighted exact text. Markdown tables preserve column alignment and inline formatting; wide tables scroll within the document. Both views read the same official file. Drag its title or use arrow keys while the title is focused to reposition it. Drag any edge or corner to resize. Focus the bottom-right resize handle and use arrow keys for keyboard resizing; Shift uses smaller steps. Minimize keeps a title bar on the canvas; removing a document from the canvas does not delete its file. Document zoom is independent of canvas zoom; its percentage button resets to 100%. Maximize fills the browser area, and Restore or Escape returns the original window size and position. Placement, dimensions, document zoom, and source-view preferences persist in this browser, separately from the official document. Refreshes preserve the reader's scroll position and do not store document copies in browser storage. No documents are created by registration. Missing or unreadable files show an error instead of a stale success state.

Only explicitly registered UTF-8 Markdown/text files are exposed, up to 20 files and 256 KB each; directories and changed symlink targets are refused. A glossary is normal; register context maps and ADRs only when the project actually has them. Other official specs or research documents may be registered when relevant, but the base grilling workflow does not promise to produce them. Standalone HTML has no filesystem access and directs readers to the live local canvas rather than presenting a document copy as live.

## Bind an agent session

Store a runtime binding in the session directory, not in project instructions:

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" bind --session-dir "$SESSION_DIR" --provider codex --agent-session "$CODEX_THREAD_ID" --transport auto
```

For Claude Code, pass `--provider claude` and its exact runtime session UUID. Never choose the most recent session or derive identity from CLAUDE.md. Inbox mode records the destination and offers an unambiguous copyable handoff; it does not promise automatic delivery.

`auto` checks the existing shared Codex daemon and reads the exact thread through its proxy. Direct delivery is enabled only when that thread is already loaded and active or idle. Otherwise binding selects inbox mode and reports why. Explicit `--transport codex-queue` refuses an unverifiable destination; `--transport inbox` skips probing. Binding never starts a daemon, resumes an unloaded chat, or creates a second runner.

Each new answer commits immediately, including durable delivery intent. A single background worker then sends `codex queue --thread <UUID> --message <prompt>` with an argv array, no shell. Slow host calls do not hold up the save response. Queued work survives a server restart; interrupted sends become uncertain rather than being retried. Changing the destination does not redirect old queued answers to another chat.

The receiving agent must confirm receipt before processing a direct prompt:

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" receive --session-dir "$SESSION_DIR" --event EVENT_ID
```

Inbox `wait` does this automatically. Repeated receipt confirmation is idempotent; replaced or acknowledged events are rejected. Publish the next useful question with `--ack` before optional research or documentation.
A successful queue exit means accepted by Codex, not processed or answered. Timeouts and ambiguous failures become "Check delivery"; do not automatically retry because the first prompt might have arrived. The durable event and stable receipt ID permit reconciliation. A failed availability check leaves the answer saved locally. A repeated HTTP submission never queues twice. Copy the saved reply if the session host cannot deliver it, after checking ambiguous delivery outcomes in chat.

The UI shows the bound provider/UUID and transport in its menu. It subscribes to local change notifications for rendering; direct mode does not depend on an agent wait loop or presence heartbeat. The local server and the session host must still be available. Unarchived does not mean reachable.

Claude Code's documented Channels mechanism can push events to an open session, but needs a channel-enabled session and does not wake a stopped one. `claude --resume ID -p` starts a resumed runner; it is not an injection into the existing interactive runner. This skill does not silently start a second Claude runner or claim a Claude direct-send adapter exists.

Sources: [Codex app-server](https://developers.openai.com/codex/app-server/), [Claude Channels](https://code.claude.com/docs/en/channels), [Claude CLI](https://code.claude.com/docs/en/cli-reference). The queue command was verified against the locally installed Codex CLI help.

## Standalone fallback

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" render --require-help --snapshot /absolute/path/session.json --output /absolute/path/canvas.html
```

Open this HTML directly. It has the same answer and review behavior, with copyable replies instead of live communication. Drafts are saved in browser storage when available, scoped by session ID. **View all questions and answers** offers copying the session message or downloading the same data as JSON. Drafts survive snapshot updates. Submitting an answer clears its matching draft; a newer edit stays intact. The export includes `session`, `answerState`, drafts, draft contexts, and pending delivery receipts. Passing the complete exported JSON to `render --snapshot` preserves all of these in a standalone canvas. Passing it to `publish --snapshot` in a new session directory with `--expected-revision 0` restores its original revision and history. Omit `--require-help` when restoring an older snapshot without prepared help. Do not extract only `session` when restoring: that loses the review history. For an existing live session, always build from its latest state; the publisher preserves its application-owned history.

## Provenance

The interview model follows Matt Pocock's [grill-me](https://github.com/mattpocock/skills/blob/main/skills/productivity/grill-me/SKILL.md), [grilling](https://github.com/mattpocock/skills/blob/main/skills/productivity/grilling/SKILL.md), and [grill-with-docs](https://github.com/mattpocock/skills/blob/main/skills/engineering/grill-with-docs/SKILL.md) workflow. Fabrica implements the visual wrapper and transport. The design-tree approach also draws on Fred Brooks' *The Design of Design*. Preserve these credits in the About dialog and documentation when redistributing the skill, along with [Matt Pocock's MIT license notice](Matt-Pocock-MIT-LICENSE.txt).

## Incremental interview

Each answer is a separate event and is eligible for processing immediately. There is no batch submission or round-completion gate. The agent reconciles that answer, adds its follow-ups, and publishes with that event's acknowledgment while unrelated questions may remain open. Durable pending events are delivery receipts, not a batch for the user to assemble.

The canvas marks newly added question IDs as **New**. When the user's submitted event is acknowledged in a published revision, it selects a ready new question, then a newly unlocked question, then another ready question. Automatic advancement only happens while the user is still on the submitted question and has no active edit or other open panel. It never invents questions or treats local submission as an agent response. Copy/paste remains explicit when automatic delivery is unavailable; full-session viewing and JSON export are reference and recovery tools.

## Replacing a submitted answer

Editing a saved answer enables **Update answer**. A replacement identifies the pending receipt it replaces, so an older tab cannot silently overwrite a newer submission. The replacement is stored atomically as a new event; the old event remains in history but is excluded from pending work. Publishing against the replaced receipt is rejected. An agent that already read the old answer must reread the latest pending event and reconcile it before publishing. Already delivered chat messages cannot be recalled.

## Delivery feedback and latency

Saving, sending, receiving, and publishing are distinct. The canvas shows **Sending to agent** while delivery is queued, **Sent to Codex** after host acceptance, and **Received by Codex** only after the agent claims the receipt. A listening inbox shows **Waiting for agent** until that claim. During processing, the saved answer remains visible and the UI explains that the next question will appear automatically. Failed or uncertain sends retain explicit recovery guidance.

Server-sent events notify the page when state, receipts, presence, or registered documents change. The server checks for cross-process changes every 100 ms; a low-frequency page refresh remains as recovery. These updates remove polling delay, but cannot eliminate model reasoning time or wake a finished chat without a supported host transport.

```sh
python3 "$SKILL_DIR/scripts/grill_ui.py" timings --session-dir "$SESSION_DIR"
```

The timing report exposes save, queue, send, receipt, and publication times where observed, plus elapsed seconds from save. Missing stages remain absent. These are application-owned receipt facts, not authored design-tree properties. Use them to distinguish transport latency from agent work rather than treating a saved answer as delivered.
