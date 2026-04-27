---
title: "Internals: atexit + lifespan"
description: Why teardown stays synchronous and silent — atexit, the FastAPI lifespan, and signal handlers.
tags: [contributing, internals]
crosslink_defines: []
crosslink_references: []
---

# Internals: atexit + lifespan

*Three teardown paths converge on `LabManager.cleanup` — the FastAPI lifespan, the signal handlers, the `atexit` hook. None run async.*

Three teardown paths, in order of how late they fire: the FastAPI lifespan (clean shutdown), the signal handlers (SIGTERM/SIGINT), and `atexit` (the last safety net). All three converge on `LabManager.cleanup`. None of them runs async code.

## atexit teardown {#atexit-teardown}

<!-- trace: neops_remote_lab/netlab/lab_manager.py:327 -->
At module import time `LabManager` registers `_atexit_cleanup` with `atexit.register`. When the interpreter exits — normally, on SIGTERM, or because pytest crashed — the hook runs and tears down any live lab.

Two non-obvious choices:

1. **`silent=True`.** The hook calls `LabManager.cleanup(silent=True)`, which suppresses logging for the duration of the call. By the time `atexit` runs, Python's logging handlers have already had their streams closed, and a routine `_log.info(...)` raises `ValueError: I/O operation on closed file`. Silent cleanup avoids the error during a path that cannot itself raise without orphaning containers.

2. **Synchronous, no async.** The teardown is plain subprocess calls to `netlab down --cleanup`. **Never add async code to this path.** Once the interpreter reaches `atexit` there is no running event loop; awaiting a coroutine or blocking on an asyncio primitive deadlocks the interpreter and the process has to be `kill -9`'d. The `LabManager` and `connector` modules are synchronous specifically so this path stays simple.

The hook also runs when a test forgot to `release()`. A test that raises before reaching its `finally` block may never call release — the `atexit` hook still fires when the pytest process exits, so a lab that would otherwise be orphaned gets cleaned up. The queue head advances on the next server tick when the session times out.

## Lifespan: the clean path

The FastAPI app uses an async context manager (`lifespan`) for startup and shutdown. On startup it cleans up any stale Netlab `default` instance left over from a crashed prior process, then launches the background cleanup loop (`_cleanup_loop_async`) that periodically sweeps stale sessions. On shutdown it cancels the cleanup task, removes all tracked sessions, and runs a final `LabManager.cleanup`.

The lifespan is the *expected* path. When it runs to completion, `atexit` finds no lab to clean up and is a no-op. The combination is intentional: the lifespan handles the 99% case cleanly, and `atexit` is the safety net for everything else.

## Signal handlers

Signal handlers for `SIGTERM`/`SIGINT` are registered at module import time, not inside the lifespan, so they are effective from the moment the process starts. The handler does the minimal thing — sets `_SHUTDOWN_EVENT` — and lets the cleanup loop and the lifespan handle the actual teardown.

Signal handlers must be minimal to avoid deadlocks; do not move teardown work into them. The kernel limits what's safe to do from inside a signal handler, and "trigger an event the main loop is watching for" is the safest possible operation.

## See also

- **[Lab Lifecycle → atexit is the last safety net](../10-concepts/30-lab-lifecycle.md#atexit-is-the-last-safety-net)** — the consumer view of the same hook.
- **[Internals: Async discipline](30-internals-async.md)** — the boundary that keeps `atexit` simple. Async on the wrong side of it deadlocks here.
- **[Internals: LabManager singleton & locking](40-internals-lab-manager.md)** — the state the teardown path operates on.
- **[Anti-patterns → Add async code to the atexit teardown](70-anti-patterns.md)** — the rule, restated next to its neighbors.
