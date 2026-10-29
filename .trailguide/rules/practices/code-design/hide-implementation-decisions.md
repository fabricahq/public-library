---
title: "Hide implementation decisions behind meaningful interfaces"
whenToRead: "Before designing, changing, or reviewing how functions, classes, packages, or services work together. Read when choosing parameters, adding configuration, passing dependencies, or deciding which module performs a step."
impact: "HIGH"
impactDescription: "Callers that repeat a module's internal steps can miss required work and must change whenever those steps change."
tags: "code-design, interfaces, information-hiding, ownership"
attribution:
  - url: https://web.stanford.edu/~ouster/cgi-bin/book.php
    description: "Informed by modules and interfaces, information hiding, different abstractions at different layers, and pulling complexity downward in John Ousterhout's A Philosophy of Software Design, second edition, chapters 4, 5, 7, and 8. Wording and examples are original."
---

## Hide implementation decisions behind meaningful interfaces

Hide implementation decisions so callers neither need to understand them nor depend on them.

A module can be a function, class, package, or service.
Its interface is everything a caller must know to use it correctly.
That includes arguments, return values, call order, who closes a resource, and what happens if a step fails.

Encapsulate an implementation decision by keeping the code and data that depend on it together in one module.
Those decisions include how to arrange stored data, which algorithm to use, and which steps must happen in what order.
The module should make those decisions and carry them out, rather than requiring callers to repeat them.

Information hiding succeeds when callers can use the module correctly without knowing those decisions.
You should be able to change a hidden decision without changing callers, as long as the module's behavior stays the same for them.
For example, callers of a document store should not need to know whether it stores documents in one file or several.

Making a field private is not enough.
If callers still need to understand its contents through getters, setters, or configuration, that information remains exposed.

Let callers ask for a result and choose the things that matter to their task, such as which document to save.
Keep the decisions about how to produce that result inside the module.

### Implementation

- Let callers ask for a result instead of making them assemble the steps that produce it.
  For example, a caller should save a document by calling `saveDocument(path, contents)`.
  The document module should create the temporary file, write to it, replace the original, and clean up if something fails.
- Ask callers for choices they need to make.
  A caller may need to choose a destination, a payment provider, or a transaction that several operations share.
  Let the module decide details such as temporary-file names and which private helper to call.
- Make each module save its callers from knowing or doing something.
  If a wrapper forwards the same arguments and returns the same result, check what else it provides, such as authorization or retries.
  If it adds nothing, remove it or move the work so each module has a clear job.
- Build and connect dependencies where the code already knows which implementations to use.
  For example, application setup can select the session fetcher without making the entry point pass that function through.
  A module's tests can supply substitutes to its factory without adding those parameters to every caller above it.
- Check what callers must understand, rather than counting arguments.
  Putting five implementation details in one options object still requires callers to know all five.
  Writing the fields explicitly or deriving them from another type does not remove that knowledge.

Keep explicit dependencies and small operations when callers need them to control the larger task.
For example, a caller may need to pass one transaction to several modules so their changes succeed or fail together.
Shared types are also useful when they describe the same data: `Pick<User, 'id' | 'name'>` need not become a separate handwritten type.
A small module that already gives callers a useful operation needs no extra wrapper.

### Rationale

When every caller repeats the steps for an operation, each can omit a step or run them in the wrong order.
Changing those steps then requires finding and updating every caller.
Putting the steps in one module means fixing them once, while callers keep asking for the same result.

Callers still need to know whether an operation writes a file, charges money, or can fail.
They should not need to know which helpers it calls or how it arranges stored data.
Renaming functions or making fields private does not help if callers still need that knowledge.

### Examples

These examples use TypeScript, but the practice applies in any language.
They show what callers use; the implementation must still do the work correctly.
A shorter call alone does not make a better module.

#### Application: Saving a document

An editor needs to save a document while other readers see either the complete old version or the complete new version.

**Incorrect (counterexample):**

```ts
const temporary = await documents.writeTemporary(path, contents);
await documents.replace(path, temporary);
```

Every caller must know to write a temporary file before replacing the original.
Each must also handle leftover files if replacement fails.
Putting `temporary` in an options object would leave those responsibilities with the caller.

**Correct:**

```ts
await documents.save(path, contents);
```

The document module creates the temporary file, replaces the original, and cleans up after failure.
The caller supplies the destination and contents.
Changing how replacement works does not require editing callers.
A successful save in this example does not guarantee that the contents survive a machine crash.

#### Application: Constructing an application

An entry point chooses the API mode and whether users must sign in.
The application already has fixed functions for fetching sessions, logging out, and clearing account state.

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

The entry point must import those functions and know where to pass them.
Adding a function to `SessionDependencies` changes what the entry point must supply, even if it has no new decision to make.
Replacing `Omit` with an explicit list of the same fields makes the type easier to read but leaves that problem in place.

**Correct:**

```ts
type ApplicationConfig = {
  apiMode: ApiMode;
  authRequired: boolean;
};

const app = createApplication({ apiMode, authRequired });
```

`createApplication` selects the session functions and connects them to account and cache cleanup.
The session module's factory still accepts dependencies, so its tests can supply controlled implementations.
Changing one of those functions does not change what the entry point must supply.
If callers need to select an authentication provider, accept that provider as configuration.

#### Application: Sharing a transaction across operations

A caller needs to save an order and reserve stock in one transaction: both changes must succeed, or neither should take effect.

**Incorrect (counterexample):**

Make `saveOrder(order)` and `reserveStock(items)` each start and commit its own transaction to avoid passing a transaction argument.
The order can then save successfully even if reserving stock fails.

**Correct:**

```ts
await database.transaction(async (tx) => {
  await orders.save(tx, order);
  await inventory.reserve(tx, items);
});
```

The caller starts the transaction because it knows the two changes must happen together.
Each module uses that transaction but keeps its queries and table layout private.
Removing the transaction argument would take away control the caller needs.

### Validation

Read the module's interface and a few places that call it.
For each argument, callback, or required sequence, ask:

- Does the caller need to choose this, such as the destination file or a shared transaction?
- Or does the caller supply it only because the module requires help with an internal step?

Before reporting a problem, name what the caller unnecessarily needs to know and which module could handle it instead.

Try a plausible internal change: add a cleanup step, change a table layout, or replace a helper.
Which callers would need edits, and why?
If their requested result stays the same, those callers should normally stay unchanged.
A change to results, accepted inputs, or an intentionally shared data format can require caller changes.

After refactoring, test the results callers depend on, including what happens if a step fails.
Check that callers can still make necessary choices, such as selecting a provider or sharing a transaction.
Neither argument counts, `Omit`, dependency injection, nor shared types prove a problem on their own.
