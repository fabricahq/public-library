---
title: "Record facts when they happen"
whenToRead: "Before planning, writing, changing, or reviewing behavior that depends on what happened earlier, such as which reply a request received, which job delivered a result, whether a question was answered, or whether an order was refunded, and before migrating records that lack such a fact."
impact: "HIGH"
impactDescription: "A fact inferred from history, such as from entry order, timestamps, or which entries ran, is wrong whenever history takes a shape the inference didn't expect, so code repeats, skips, or misattributes work, and each patch to the inference invites the next."
tags: "code-design, state, events, data-modeling, migrations"
---

## Record facts when they happen

When behavior depends on what happened before, record that fact durably at the moment it happens, and derive state from the record.
Don't infer the fact later from patterns in history, such as the order of entries, timestamps, or which entries exist.

### Implementation

- State the fact the behavior depends on as a sentence, such as "this reply answers that question" or "this refund reverses that payment."
  If no stored field or record says that sentence, add one.
- Write the fact in the operation where it happens, in the same transaction or write as the event, so the event and its record can't disagree.
  Include the identifiers that link it, such as the question a reply answers or the payment a refund reverses.
- Derive state by reading those records: a refunded payment is one a refund record names, and an open question is one that no reply names.
  A cache or projection of the records is fine when it can be rebuilt from them.
- When existing records predate the fact, don't reconstruct it by inference, in a backfill or in a fallback at read time.
  Settle the old cases explicitly instead: give them one stated outcome, chosen from the behavior they had when they happened, and mark them as settled without the fact.
  Record the fact for every new event from the change on.

These cases comply:

- An event log whose events state the fact is the record, so deriving state from those events complies.
  What the rule forbids is reconstructing a fact that no event states.
- When another system owns the fact and can answer for it, such as a payment provider's refund API, reading the fact from that system complies.
- Patterns in history are fine for estimates that drive no behavior, such as a trend on a dashboard.

### Rationale

An inference holds only for the histories its author imagined.
Retries, concurrent work, edits, partial failures, and new features produce histories it didn't expect, and it then answers wrong without raising an error.
Each wrong answer gets patched with another condition, the conditions interact, and the mechanism never settles.
A fact recorded when it happens doesn't depend on what happens later: the code that knew the answer wrote it down, so no code has to guess it.

Reconstructing a missing fact for old records brings the inference back, and is usually harder than the original, because old history was never shaped to answer the question.
An explicit settlement of old cases is one decision a reviewer can check once.
An inference is a guess that every later change must keep right.

### Examples

This practice applies in any language and with any storage.
The TypeScript examples illustrate it.

#### Application: Deciding whether a payment was refunded

A cancellation flow refunds an order's payment unless it was already refunded.
The order's payment entries include charges, refunds, chargebacks, and manual corrections, each stored as a signed amount.

**Incorrect (counterexample):**

```ts
function alreadyRefunded(order: Order): boolean {
  return order.payments.some((entry) => entry.amount < 0);
}
```

A negative entry can be a chargeback or a correction, so the flow skips a refund the customer is owed.
A refund the provider hasn't settled yet has no negative entry, so cancelling twice refunds twice.
Patches such as checking the entry's memo or comparing its timestamp with the cancellation's each add a condition that the next history breaks.

**Correct:**

```ts
type Refund = { readonly paymentId: string; readonly amount: number };

/** Record the refund and queue it for the provider in one transaction. */
async function refundPayment(tx: Transaction, payment: Payment): Promise<void> {
  await tx.insert('refunds', { paymentId: payment.id, amount: payment.amount });
  await tx.insert('provider_requests', { kind: 'refund', paymentId: payment.id });
}

/** True when a refund record names the payment; payment entries aren't consulted. */
function alreadyRefunded(refunds: ReadonlyArray<Refund>, payment: Payment): boolean {
  return refunds.some((refund) => refund.paymentId === payment.id);
}
```

The refund record exists from the moment the flow decides to refund, so a second cancellation sees it while the provider is still processing.
A chargeback writes no refund record, so it can't be mistaken for one.
The queue table is illustrative; what matters is that the record commits together with the event it describes.

#### Application: Payments from before the record existed

Payments taken before the refund records were added have none.
Their refunds were issued by hand, by support staff in the provider's dashboard.

**Incorrect (counterexample):**

```ts
// Backfill: treat a negative entry within 30 days of a charge as its refund.
for (const order of ordersBeforeRefundRecords) {
  for (const charge of order.payments.filter((entry) => entry.amount > 0)) {
    const refund = order.payments.find(
      (entry) => entry.amount === -charge.amount && withinDays(charge.createdAt, entry.createdAt, 30),
    );
    if (refund) await db.insert('refunds', { paymentId: charge.id, amount: charge.amount });
  }
}
```

The backfill is the same inference in a new place.
Its records look observed but are guesses, and the first mismatch gets another condition.

**Correct:**

```ts
// Refunds before the refund records were manual, so automation leaves these payments to support.
await db.update('payments', { createdBefore: REFUND_RECORDS_START }, { refundHandling: 'manual' });

function canRefundAutomatically(payment: Payment): boolean {
  return payment.refundHandling !== 'manual';
}
```

Old payments keep the behavior they had: support handles their refunds.
The `manual` marker is the settlement, stated once for the payments from before the change, so no one mistakes it for observed history.
Every new refund is recorded when it happens.

### Validation

For each behavior that depends on an earlier event, find the field or record that states the fact, and the code that writes it where the event happens, together with the event.
Then check that the decision reads that record.

Look for decisions computed from entry order, the first or latest entry, timestamps compared across records, counts, or which entries ran, and for fallbacks that handle records missing the fact.
Each is a likely inference.
Check for a test whose history makes the pattern and the fact disagree, such as a chargeback that isn't a refund or a job that ran twice, and that asserts the behavior follows the record.
For a migration, check that old records get an explicit, labeled settlement, and that no code reconstructs the fact for them.

These are not by themselves evidence of a violation: sorting entries by time for display; reading the latest entry when "latest" is the specified meaning, such as the current setting being the most recent edit; deriving state from an event log whose events state the fact; and reading the fact from the system that owns it.
