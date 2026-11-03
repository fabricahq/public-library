---
title: "Apply asynchronous results only while they remain valid"
whenToRead: "Before planning, implementing, changing, or reviewing overlapping requests, background refreshes, retries, or saves that update the same state, or operations that can finish after their target, account, or session changes."
impact: "HIGH"
impactDescription: "Obsolete results can overwrite newer content, restore invalid permissions, or put one account's data into another account's state."
tags: "concurrency, async, ordering, lifecycle, caches"
---

## Apply asynchronous results only while they remain valid

Apply an asynchronous result only while it still belongs to the intended owner and is permitted to update the destination state under the operation's contract.
Enforce this at every path that can publish a result, including background reads and cache updates.

### Implementation

- Identify the destination state, its owner, and the contract that determines which results it may accept.
  The owner may be a document session, an account's cache, or a shared record whose lifetime exceeds the initiating screen's.
- Choose the ordering policy from that contract.
  Request order, completion order, and data revision are different facts: starting or finishing later does not prove that a response contains newer data.
  Use the relevant guarantee, such as an owner generation, a data revision, serialization, or a defined merge operation.
- Enforce acceptance when the result updates state.
  Recheck after any intervening wait that could invalidate the decision, or use an atomic conditional update when other writers can race with the check.
  Protect failure results too when they change the destination's state.
- Include all writers in the policy, such as prefetches, foreground reads, background refreshes, and save responses.
  Guarding the visible screen's request is insufficient when another path can still overwrite the same cache.
- Use cancellation to reduce obsolete work, and establish whether it also prevents results from being applied.
  If the transport or library can still deliver a result after cancellation, prevent that result from changing state when it is no longer valid.
  A library that already enforces the required policy needs no duplicate application-level guard.

Apply the policy to the destination, not just to the initiating caller's lifetime.
A canceled screen can leave useful shared work running, and independent results or updates that can safely merge need not discard all but the latest request.
Ignoring a response does not undo a server-side write; conflicting writes require an appropriate policy at the server's write boundary too.

### Rationale

An operation can be valid when it starts and obsolete when it finishes.
Checking one request's lifetime does not protect shared state from another writer that bypasses that check.
A coherent acceptance policy prevents completion timing from silently deciding which content or permissions users see.

### Examples

#### Application: A prefetch finishes after validation

An editor starts a background prefetch and a separate validation read for the same document.
The validation returns newer metadata showing that the document is trashed, so the editor becomes read-only.
The prefetch then returns older metadata showing an active document.

**Incorrect (counterexample):**

The validation checks that its session is still current, but the prefetch writes directly into the shared cache.
Its late response replaces the validated metadata and makes the editor writable again.

**Correct:**

The state owner prevents the obsolete prefetch from replacing the validated result.
For example, it can cancel the pending cache read before publishing the validated result if the cache library guarantees that canceled reads cannot later publish their responses.
If cancellation cannot provide that guarantee, enforce acceptance at the cache update boundary, such as by comparing authoritative data revisions.
Keep the validation itself current across any wait introduced by cancellation.

#### Application: An account changes while a save is pending

An account's save request remains in flight when the user switches accounts.
The new account has its own cache and visible editor state.

**Incorrect (counterexample):**

The save's success callback writes its response into whichever account cache is active when it finishes.
An error callback can likewise display the old account's save failure in the new editor.

**Correct:**

Bind the operation to its initiating account and destination.
When it finishes, apply success or failure only to a destination that still accepts results from that owner.
A generation check can prevent an old callback from updating a replacement account session; an intentionally retained account-specific cache can accept its own results if its contract permits it.
The server may still complete the save for the original account, independently of whether the replacement UI accepts the response.

### Validation

Inspect every path that writes the affected state, including library-managed cache writes, and name the ownership and ordering guarantees each relies on.
Before reporting a violation, identify a permitted completion order that produces an incorrect observable result; multiple requests alone are insufficient evidence.

Control completion order with held responses or test-controlled signals rather than timing sleeps:

- Hold competing operations pending, release them in the problematic order, and assert the protected outcome through the supported interface, such as retained content or editability.
- Where owner replacement or disposal matters, release an old result afterward and verify it cannot affect the replacement owner. Include failures when they update state.
- Verify results that remain valid still take effect, including shared work that intentionally outlives its initiating caller.

Use the lowest test layer that includes the competing writers and their actual acceptance mechanism.
An assertion that cancellation was called does not establish that an obsolete response cannot change state.
