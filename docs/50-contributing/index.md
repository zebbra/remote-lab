---
title: Contributing
description: Invariants you must preserve, internals you should understand, and the dev-setup workflow for changing the neops-remote-lab codebase.
tags: [contributing, reference, internals]
crosslink_defines: []
crosslink_references: []
---

# Contributing

Two readers. Most pages assume you are about to **change the codebase** — open a PR that fixes a bug, adds a capability, refactors internals, or bumps a dependency. The same pages double as the deep reference for a **senior consumer** who wants to understand why the system behaves the way it does before trusting it in production.

What you will not find here: a "how to call the API" tutorial — that's the [Quickstart](../getting-started/10-quickstart.md) and the [Pytest Fixtures](../20-client/10-pytest-fixtures.md) reference. The [REST API](../30-server/10-rest-api.md) reference is authoritative for the HTTP surface.

## In this section

| Page | What it covers |
|---|---|
| [Dev setup](10-dev-setup.md) | Cloning the repo, the `make check` pipeline, code style and type-check rules, the CVE-pinned dependency convention, the branch-to-PR flow. Run this once, then come back when CI surprises you. |
| [Invariants](20-invariants.md) | The eight load-bearing rules a change cannot break. Each entry: rule, why, what breaks. Read before touching server, queue, or lab-manager code. |
| [Internals: Async discipline](30-internals-async.md) | `_run_blocking`, the async/sync boundary, the single Netlab invocation path. The mechanics behind "long Netlab calls don't block the queue". |
| [Internals: LabManager singleton + locking](40-internals-lab-manager.md) | The classmethod-only singleton, `try_acquire` vs `acquire`, GLOBAL_LOCK, stale-state recovery. The synchronous half of the codebase. |
| [Internals: atexit + lifespan](50-internals-atexit.md) | The three teardown paths (lifespan, signal handlers, atexit), why they all stay synchronous, and what `silent=True` is protecting against. |
| [Internals: CI test stubbing](60-internals-test-stubbing.md) | The `StubLabManager` pattern, the pytest plugin entry point, and why the singleton design makes both possible. |
| [Anti-patterns](70-anti-patterns.md) | A grep target. Every load-bearing rule restated as a code-review trigger, with a link to the page that explains why. |

## Where contributor knowledge lives

| Source | Purpose | When to read |
|---|---|---|
| [Invariants](20-invariants.md) + the four Internals pages | The rules and the mechanics that enforce them. | Before modifying server, queue, or lab-manager code; before reasoning about edge cases as a power consumer. |
| [Anti-patterns](70-anti-patterns.md) | A one-page grep target for code review. | When reviewing a PR that touches the load-bearing surface. |
| [`AGENTS.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/AGENTS.md) | The same invariants in repo-root form, alongside agent-bootstrap context. | When working with an AI assistant, or when you want a one-screen recap with no narrative. |
| [`README.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/README.md) | Project overview, install, quick orientation. | First contact. |
| Source code itself | The truth. Trace comments in this section's pages point at the relevant lines. | When the docs and the code disagree — file a docs issue and trust the code. |

## What to read next

- **[Dev setup](10-dev-setup.md)** — start here if your dev environment is not yet running `make check` green.
- **[Invariants](20-invariants.md)** — start here if your dev environment is fine and you are about to change something load-bearing.
- **[Architecture](../10-concepts/10-architecture.md)** — the high-level picture of how the components fit together. The Internals pages assume you have read this.
