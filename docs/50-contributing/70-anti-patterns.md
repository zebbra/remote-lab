---
title: Anti-patterns
description: The consolidated "don't" table for neops-remote-lab — every load-bearing rule restated as a code-review trigger, with a link to the page that explains why.
tags: [contributing, reference]
crosslink_defines: []
crosslink_references: []
---

# Anti-patterns

*A grep target for code review. Every load-bearing rule restated as a code-review trigger, with a link to the page that explains why.*

A grep target. When reviewing a PR, scan for any of the patterns below and link the relevant row in your review. Each row links to the page with the full reasoning.

| Don't | Why | See |
|---|---|---|
| Shell out to `netlab` directly. | Bypasses logging, error handling, `expected_failure`, the stream toggle. | [Async discipline → Single Netlab invocation path](30-internals-async.md#single-netlab-invocation-path) |
| Do blocking I/O in an async handler without `_run_blocking`. | Stalls the event loop; every poll from every other client backs up. | [Async discipline](30-internals-async.md#async-and-blocking-discipline) |
| Add async code to the `atexit` teardown. | No event loop at exit; deadlocks the interpreter. | [atexit + lifespan](50-internals-atexit.md#atexit-teardown) |
| Drop the `*Dto` suffix on a request/response model. | Convention is load-bearing for code review and reasoning. | [Invariants → `*Dto` suffix](20-invariants.md#dto-suffix) |
| Remove a `# CVE-*` comment on a dependency upgrade. | Pin reasoning is silent metadata; deletion regresses the security gate. | [Invariants → CVE-pinned dependencies](20-invariants.md#cve-pinned-dependencies) |
| Run two `neops-remote-lab` servers on the same host. | Filelock catches it, but only after both processes log noise; the underlying constraint is real. | [Invariants → One server instance per host](20-invariants.md#one-server-instance-per-host) |
| Run `netlab` by hand while the server is running. | State divergence; the server's `default` instance and your manual one collide. | [Invariants → One lab per host](20-invariants.md#one-lab-per-host) |
| Call `acquire` (the polling variant) from inside the server's event loop. | Loop blocks; release that would unblock you cannot land. | [LabManager → `try_acquire` vs `acquire`](40-internals-lab-manager.md#try_acquire-vs-acquire) |
| Add code to `LabManager` or `connector.py` that imports `asyncio`. | Crosses the sync/async boundary the other direction; no benefit, fragile teardown. | [Async discipline](30-internals-async.md#async-and-blocking-discipline) |
| Add a topology-accepting entry point that doesn't accept both `.yml` and `.yaml`. | Surface asymmetry; "topology accepted, then mysteriously rejected" failures. | [Invariants → `.yml` and `.yaml` are both accepted](20-invariants.md#yml-and-yaml-are-both-accepted) |
| Add a second auth path (Bearer, mTLS, header magic) without removing the X-Session-ID gate. | Confused threat model; callers get to choose which boundary to bypass. | [Invariants → X-Session-ID is the only access boundary](20-invariants.md#x-session-id-is-the-only-access-boundary-on-lab) |
| Write a test that depends on stub-only behaviour and passes in CI. | Stub diverges from real Netlab at the boundary; the test hides the divergence. | [CI test stubbing](60-internals-test-stubbing.md#tests-that-need-real-netlab) |

## See also

- **[Invariants](20-invariants.md)** — the rules each anti-pattern violates, in long form.
- **[Internals: Async discipline](30-internals-async.md)** — the boundary most of the entries above police.
- **[Internals: LabManager singleton & locking](40-internals-lab-manager.md)** — `try_acquire` vs `acquire` in detail.
