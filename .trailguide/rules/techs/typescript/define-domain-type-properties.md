---
title: "Define every property of a domain type"
whenToRead: "Before planning, writing, changing, or reviewing a TypeScript type alias or interface, especially one that represents a business concept, or a property whose optional or null value, invariants, or references to another module carry rules."
impact: "MEDIUM"
impactDescription: "Domain terms that look self-describing, such as status or balance, are guessed at and misused when their meaning, units, and lifecycle aren't written down."
tags: "typescript, comments, tsdoc, domain, types"
---

## Define every property of a domain type

In a domain type or interface, give every property a one-sentence TSDoc comment defining what the term means in this domain, including units, scope, and lifecycle when they apply.
Outside domain types, comment a property only for what its name and type can't show: what an optional or null value means, an invariant it takes part in, or a reference to something another module owns.

### Implementation

- A domain type represents a business concept rather than plumbing or transport, such as the types in a `domain/` or `model/` module.
  An API request or response shape, a form's state, a component's props, or a configuration object is not a domain type.
- Write the comment as `/** ... */` directly above the property, so editors show it on hover.
- Define the term, not the type: "Amount still owed, in cents" rather than "The balance number."
- Outside domain types, skip properties whose name and type already say everything.

### Examples

#### Application: A domain type

**Incorrect (counterexample):**

```ts
type Invoice = {
  status: 'draft' | 'open' | 'paid' | 'void';
  balance: number;
  dueOn: string;
};
```

The literal union lists the statuses but not what moves an invoice between them, and nothing says the balance's unit or the due date's time zone.

**Correct:**

```ts
type Invoice = {
  /** Draft until sent, then open until paid in full or voided. */
  status: 'draft' | 'open' | 'paid' | 'void';
  /** Amount still owed, in cents, after payments and credits applied so far. */
  balance: number;
  /** Calendar day, as `YYYY-MM-DD` in the account's time zone, by which payment is owed. */
  dueOn: string;
};
```

#### Application: A non-domain type

**Correct:**

```ts
type InvoiceListResponse = {
  invoices: ReadonlyArray<Invoice>;
  /** Absent on the last page. */
  nextCursor?: string;
};
```

Only the optional property carries a meaning its type can't show, so only it gets a comment.

### Validation

In domain types, check that every property has a one-sentence definition of the term, not a restatement of its name.
Outside domain types, check that each uncommented optional, nullable, or cross-module property has a meaning obvious from its name and type.

A self-describing property outside a domain type without a comment is not a violation.
