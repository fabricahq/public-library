---
title: "Hide implementation decisions behind meaningful interfaces"
whenToRead: "Before planning, writing, changing, or reviewing interfaces between functions, classes, packages, or services, such as choosing parameters, defining configuration, exposing dependencies, or dividing an operation across callers and modules."
impact: "HIGH"
impactDescription: "Interfaces that expose implementation decisions spread required knowledge across callers, invite inconsistent behavior, and make internal changes require coordinated edits."
tags: "code-design, interfaces, information-hiding, ownership"
attribution:
  - url: https://web.stanford.edu/~ouster/cgi-bin/book.php
    description: "Informed by information hiding, different abstractions at different layers, and pulling complexity downward in John Ousterhout's A Philosophy of Software Design, second edition, chapters 5, 7, and 8. Wording and examples are original."
---

## Hide implementation decisions behind meaningful interfaces

Give callers operations that express what they want to accomplish.
Keep the knowledge needed to implement those operations inside the module that owns them, and expose a choice when callers have a legitimate reason to make it.

A module can be a function, class, package, or service.
Its interface includes everything callers must know to use it correctly: parameters and results, required call order, resource ownership, and failure behavior.

### Implementation

- When a module exposes an operation, implement the steps needed to deliver its documented result inside that module, including required ordering and failure cleanup.
  For example, if `saveDocument` promises to replace a file safely, it should create the temporary file, replace the destination, and handle cleanup itself; callers should supply the destination and contents.
  Document what callers can expect on success and failure, without making them reproduce the internal procedure.
- Accept inputs, policies, and resources that callers own or need to select.
  Choose internal mechanisms in the module responsible for them, using the information it already has.
  Add configuration when the caller has a meaningful choice, rather than exposing every decision the implementation makes.
- Give adjacent layers distinct responsibilities.
  When a layer forwards most of another layer's interface, check what knowledge or coordination it saves callers.
  Move responsibilities or combine layers when the extra interface adds no such benefit.
- Keep construction details in the module that assembles the collaborators.
  An internal factory can accept dependencies without making every higher-level caller supply those same dependencies.
  Keep testing seams at the module they exercise rather than propagating them through unrelated interfaces solely for tests.
- Judge the knowledge required, not the number of arguments or declarations.
  An options object still exposes every decision its caller must make.
  Deriving a higher-level type from internal dependencies, or spelling out the same fields explicitly, does not hide those decisions.

Explicit dependency injection, low-level primitives, and configurable policies are appropriate when they serve the intended callers.
A projection of an existing contract can legitimately share its types.
Neither a derived type nor a repeated parameter is by itself a violation.
Identify the implementation knowledge a caller unnecessarily needs before changing the design; a small, cohesive module needs no additional layer merely to follow this rule.

### Rationale

When callers know an operation's internal recipe, each caller must reproduce it correctly and change when the recipe changes.
A module that owns the recipe lets callers depend on its guarantees instead.
This keeps implementation changes local and makes correct use require fewer decisions.

Hiding information does not mean concealing side effects or failures.
It means giving callers a useful contract without requiring them to understand how it is fulfilled.
A wrapper that renames the same steps, a larger configuration object, or private fields exposed through getters can leave the required knowledge unchanged.

### Examples

These interface sketches use TypeScript, but the practice applies in any language.
The implementations must fulfill the stated contracts; the shorter calls alone do not establish correctness.

#### Application: Saving a document without exposing the replacement protocol

An editor's callers need to save complete document contents while concurrent readers see either the previous version or the new one.

**Incorrect (counterexample):**

```ts
const temporary = await documents.writeTemporary(path, contents);
await documents.replace(path, temporary);
```

Every caller must know the temporary-file protocol, the required order, and who cleans up after failure.
A caller can leave a temporary file behind or substitute an unsafe direct write.
Bundling `temporary` into an options object would not remove that knowledge.

**Correct:**

```ts
await documents.save(path, contents);
```

The document module owns temporary-file placement, replacement, and failure cleanup.
Its contract states that readers see a complete version and explains what a reported failure means for the saved contents.
Crash durability is a separate guarantee that must be stated if provided; the method name alone does not promise it.
Callers supply the document and destination, not the replacement protocol.

#### Application: Constructing an application without forwarding its internal recipe

An entry point selects the runtime mode and whether authentication is required.
Session fetching, logout, and account cleanup have fixed implementations for this application.

**Incorrect (counterexample):**

```ts
type ApplicationConfig = Omit<SessionDependencies, 'clearCache'>;

const app = createApplication({
  apiMode,
  authRequired,
  fetchSession,
  logOutServer,
  resetAccountState,
});
```

The entry point must import the internal collaborators and understand their roles just to forward them.
Adding another session dependency changes application configuration even if callers have no new choice to make.
Replacing `Omit` with an explicit list of the same fields would improve readability without changing this responsibility.

**Correct:**

```ts
type ApplicationConfig = {
  apiMode: ApiMode;
  authRequired: boolean;
};

const app = createApplication({ apiMode, authRequired });
```

Application assembly selects and connects the fixed session collaborators and cache cleanup internally.
The session module can still have a factory that accepts dependencies for its own callers and tests.
An internal collaborator can change without changing the entry point's interface.
If the application instead supports a caller-selected authentication provider, that provider is a legitimate configuration choice.

#### Application: A caller-owned transaction is a valid dependency

A caller needs to save an order and reserve stock in one transaction.

**Incorrect (counterexample):**

Make `saveOrder(order)` and `reserveStock(items)` each start and commit a hidden transaction merely to shorten their interfaces.
The caller can no longer make the two changes atomic; one can commit while the other fails.

**Correct:**

```ts
await database.transaction(async (tx) => {
  await orders.save(tx, order);
  await inventory.reserve(tx, items);
});
```

The caller owns the transaction because the larger operation spans both modules.
Passing it explicitly preserves a required capability; each module still hides its queries and storage layout.
Do not remove a dependency whose ownership belongs to the caller, or introduce a higher-level operation without a real owner for that responsibility.

### Validation

Read the interface and representative callers together.
For each parameter, callback, or required sequence, identify whether it expresses caller intent, caller-owned policy or resources, or an internal mechanism.
For a proposed finding, name the unnecessary knowledge, the caller that must carry it, and the module that could own it instead.

Consider a plausible internal change, such as replacing a storage layout, adding a cleanup step, or changing a fixed collaborator.
Check which callers would need edits and why.
An internal change should normally stay within its owning module; a deliberate change to observable behavior or a genuinely shared contract can require caller changes.

When refactoring, verify the operation's observable guarantees and failure behavior through its interface.
Also check that legitimate caller choices, such as transaction scope or provider selection, remain possible.
Helper counts, parameter counts, `Omit`, dependency injection, and shared types are not sufficient evidence of a violation.
