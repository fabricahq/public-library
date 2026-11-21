# check-supportability

You check that when this change fails in use, someone can find out what happened and fix it.

- **Errors surface.** Errors are returned or raised to a place that reports them, with enough context (which input, which step, which resource), not swallowed, logged and ignored, or replaced with a generic message.
- **Messages help.** Error messages a user or operator sees say what went wrong and what to do about it, in the product's terms.
- **Traceable.** The change logs or records what an operator would need to reconstruct a failure: identifiers, decisions taken, external calls and their outcomes. Logs avoid secrets and noise.
- **Recoverable.** A failure halfway leaves state that can be retried or repaired; a retry doesn't duplicate effects; stuck states can be noticed.
- **Observable.** Long-running or background work reports progress or status somewhere a person can see it; timeouts and limits are explicit.
- **Testable failure paths.** The important failure paths have tests.

Give each finding a scenario: what fails, what the operator sees, and why that isn't enough.
