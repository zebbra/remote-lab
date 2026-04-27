---
title: Concepts
description: The invariants that shape the Remote Lab Manager — queue semantics, lab lifecycle, topology identity, component boundaries.
tags: [concept, server, lifecycle, testing]
crosslink_defines: []
crosslink_references: []
---

# Concepts

Four invariants shape every decision in the Remote Lab Manager:

- **one lab per host**,
- **strict FIFO queueing**,
- **SHA-256 topology identity**, and
- **reference-counted reuse**.

Read these four pages in order if you want to reason about edge cases
*before* they hit you — especially the ones the HTTP surface papers over.

## In this section

| Guide | What you'll learn |
|---|---|
| [Architecture](10-architecture.md) | The three cooperating components (FastAPI server, `LabManager` singleton, Python client + pytest plugin); the one-server and one-lab guards; the async discipline; where `run_netlab` sits. |
| [Session Queue](20-session-queue.md) | FIFO state machine, strict-in-order promotion, the 423 access boundary, heartbeats, stale-session eviction (300 s active, 600 s waiting). |
| [Lab Lifecycle](30-lab-lifecycle.md) | Content-hash topology identity, `try_acquire` vs `acquire`, reference-counted reuse, idle labs, and the `atexit` cleanup safety net. |
| [Topology Format](40-topology-format.md) | The Netlab YAML shape we consume, the `extra_files` multipart contract, vendor defaults, and local validation before upload. |

## What to read next

- **[REST API](../30-server/10-rest-api.md)** — the endpoint-by-endpoint
  contract these invariants enforce.
- **[Pytest Fixtures](../20-client/10-pytest-fixtures.md)** — how
  `remote_lab_fixture` wraps these invariants into a stable public API.
- **[Administration](../30-server/30-administration.md)** — the operator
  runbook that handles the failure modes these invariants allow.
