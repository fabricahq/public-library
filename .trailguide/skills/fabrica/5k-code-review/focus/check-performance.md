# check-performance

You look only for performance problems that are unacceptably large for this change. Do not report micro-optimizations or speculative concerns.

- Estimate realistic sizes for the data and traffic the changed code handles, from the repository's context. State your assumptions.
- Look for work that grows faster than it should: queries inside loops (N+1), repeated full scans, quadratic algorithms over collections that can be large, loading whole datasets into memory, unbounded caches or queues.
- Look for blocking calls on hot or latency-sensitive paths, missing timeouts on network calls, and serialized work that is independent.
- Check database changes for missing indexes on new query patterns and for migrations that lock or rewrite large tables.

Report a finding only when you can say roughly how bad it gets at a realistic size, for example "one query per item; 10,000 items per request in normal use". If nothing qualifies, return no findings.
