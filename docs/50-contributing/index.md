---
title: Contributing
description: Invariants you must preserve, internals you should understand, and the dev-setup workflow for changing the neops-remote-lab codebase.
tags: [contributing, reference, internals]
crosslink_defines: []
crosslink_references: []
---

# Contributing

This section is for two readers. Most pages assume you are about to **change
the codebase** — open a PR that fixes a bug, adds a capability, refactors
internals, or bumps a dependency. The same pages are also the deep reference
for a **senior consumer** who wants to understand why the system behaves the
way it does before trusting it in production.

What you will not find here: a "how to call the API" tutorial — that's the
[Quickstart](../getting-started/10-quickstart.md) and the
[Pytest fixtures](../20-client/10-pytest-fixtures.md) reference. The
[REST API reference](../30-server/10-rest-api.md) is authoritative for the
HTTP surface.

## In this section

| Page | What it covers |
|---|---|
| [Dev setup](10-dev-setup.md) | Cloning the repo, the `make check` pipeline, code style and type-check rules, the CVE-pinned dependency convention, the branch-to-PR flow. Run this once, then come back when CI surprises you. |
| [Invariants & internals](20-invariants.md) | The load-bearing rules a change cannot break (one server per host, one lab per host, content-hash topology identity, `*Dto` suffix, the `_run_blocking` discipline, the atexit teardown), and the internal mechanics that make those rules work (`LabManager` singleton, `try_acquire` vs `acquire`, the test-stubbing pattern, the single Netlab invocation path). Read before touching server, queue, or lab-manager code. |

## Where contributor knowledge lives

| Source | Purpose | When to read |
|---|---|---|
| [Invariants & internals](20-invariants.md) | The rules and mechanics for the user-facing docs site. | Before modifying server, queue, or lab-manager code; before reasoning about edge cases as a power consumer. |
| [`AGENTS.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/AGENTS.md) | The same invariants in repo-root form, alongside agent-bootstrap context. | When working with an AI assistant, or when you want a one-screen recap with no narrative. |
| [`README.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/README.md) | Project overview, install, quick orientation. | First contact. |
| Source code itself | The truth. Trace comments in this section's pages point at the relevant lines. | When the docs and the code disagree — file a docs issue and trust the code. |

## What to read next

- **[Dev setup](10-dev-setup.md)** — start here if your dev environment is not
  yet running `make check` green.
- **[Invariants & internals](20-invariants.md)** — start here if your dev
  environment is fine and you are about to change something load-bearing.
- **[Architecture](../10-concepts/10-architecture.md)** — the high-level
  picture of how the components fit together. The Invariants page assumes you
  have read this.
