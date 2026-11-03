---
title: "Define every domain field, and comment other struct fields whose meaning the type does not show"
whenToRead: "Before planning, writing, changing, or reviewing Go struct fields, especially fields of domain types, and fields whose nil or zero values, ownership, or relationships to other fields carry rules that other packages rely on."
impact: "MEDIUM"
impactDescription: "Domain terms and invariants hidden in field meanings are rediscovered by trial and error, while filler comments teach readers to skip comments altogether."
tags: "go, comments, structs, invariants, domain"
---

## Define every domain field, and comment other struct fields whose meaning the type does not show

In domain types, give every field a one-sentence comment defining what the term means in this domain, including units, scope, and lifecycle when they apply.
Fields like `Status` or `Balance` look self-describing but rarely are.
When the field's type is a reusable domain type, such as `Money` or `InvoiceStatus`, that type's doc comment owns the shared meaning: the field's comment states only its particular role or extra constraints.
Outside domain types, comment a field only when its meaning includes a durable fact that its name and type cannot express, and skip fields whose name and type already say everything.

### Implementation

Put a short comment after the field on the same line when it fits within the line length the project uses; otherwise put it on the line above.

A domain type is a struct that represents a business concept rather than plumbing or transport, such as the types in a `domain/` or `model/` package.
A request or response DTO, a database row struct, a config struct, or a service struct holding dependencies is not a domain type.

Outside domain types, comment a field when at least one of these applies:

- **Nil or zero meaning:** a nil pointer or zero value means something specific, such as "the document has no saved versions".
- **Invariants and ownership:** the field takes part in a rule enforced elsewhere, such as "at most one draft per document" or "nil exactly when `LatestVersionID` is nil".
- **References across modules:** the field holds an identifier owned by another module or service under an explicit contract.
- **Role of a dependency:** in a service struct, what a dependency is used for here, beyond what its type says.

Also:

- Describe properties, not operations: "nil while the document has no saved versions" stays true, while "set by save-version" goes stale when the call flow changes.
  Behavior belongs in a comment on the operation.
- Put facts about the whole type, such as "versions are immutable", in the type's doc comment.
- Outside domain types, skip self-describing fields such as `Name` or `CreatedAt`.
- When a comment only restates the name, delete it, or rename the field.

### Rationale

Other packages build on what a field's values mean, not just its type.
When a nil pointer carries a special meaning, a reader without the comment treats it as "not loaded yet" and writes code that breaks the rule.
Comments that restate names add nothing and train readers to skip the comments that matter.

### Examples

#### Application: A domain type

**Incorrect (counterexample):**

```go
type Invoice struct {
	Status  string
	Balance int64
	DueOn   time.Time
}
```

Each field looks self-describing, but a reader can't tell which statuses exist, what unit the balance is in, or whether it includes payments already made.

**Correct:**

```go
type Invoice struct {
	// Status is draft until the invoice is sent, then open until it is paid in full or voided.
	Status string
	// Balance is the amount still owed, in cents, after payments and credits applied so far.
	Balance int64
	// DueOn is the customer's calendar day by which payment is owed, in the account's time zone.
	DueOn time.Time
}
```

#### Application: A field whose type owns the term

**Incorrect (counterexample):**

```go
// Money is an amount in the smallest unit of its currency.
type Money struct {
	Amount   int64
	Currency string
}

type Invoice struct {
	Balance Money // Balance is an amount in the smallest unit of its currency.
}
```

The field repeats `Money`'s definition, so the two can drift apart.

**Correct:**

```go
type Invoice struct {
	Balance Money // still owed after payments and credits applied so far
}
```

The field states only its role; `Money` keeps the meaning of the amount.

#### Application: A non-domain struct

**Incorrect (counterexample):**

```go
type documentRow struct {
	ID              string
	FolderID        string
	LatestVersion   *DocumentVersion
	LatestVersionID *string
	// CreatedAt is the creation timestamp.
	CreatedAt time.Time
}
```

`FolderID` and `LatestVersionID` carry rules the types cannot show, while the only comment repeats a field name.
This database row struct isn't a domain type, so self-describing fields stay uncommented.

**Correct:**

```go
type documentRow struct {
	ID string
	// FolderID is required; documents at the top level point at the scope's hidden root folder.
	FolderID string
	// LatestVersion is the loaded row for LatestVersionID; it is nil exactly when LatestVersionID is nil.
	LatestVersion *DocumentVersion
	// LatestVersionID is nil while the document has no saved versions.
	LatestVersionID *string
	CreatedAt       time.Time
}
```

### Validation

In domain types, check that every field has a one-sentence definition of the term or, when its type owns the term, of its role, and not a restatement of its name.
For each commented field, check that the comment would stay true if the methods that write the field changed but the field's meaning did not.
For each uncommented field with a pointer, zero-value, or cross-module meaning, check that its meaning is obvious from the name and type.

A self-describing field outside a domain type without a comment is not a violation.
