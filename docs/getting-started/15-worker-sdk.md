---
title: Plug into Worker SDK
description: For Neops dev teams using the Worker SDK — install neops-remote-lab, set REMOTE_LAB_URL, then dive into the Worker SDK's testing guide for the fixture patterns.
tags: [tutorial, testing, worker-sdk]
crosslink_defines: []
crosslink_references: [remote-lab]
---

# Plug into Worker SDK

*If you write [function blocks](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/) and need a real Netlab topology to test them against, the Remote Lab side is two lines of setup. The patterns live in the [Worker SDK testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/) — this page hands you off cleanly.*

!!! tip "Wrong page?"
    Just want to run a pytest test against a real topology, not via Worker SDK? The plain [pytest path](10-pytest.md) is shorter. Driving from a non-Python stack? See [Drive from cURL](30-curl.md).

## What you need

- The Worker SDK already in your project (`pip install neops-worker-sdk`).
- A reachable Remote Lab Manager — see [Run locally](20-local.md) if you don't have one yet.
- `pytest` already in your test environment.

## Two setup steps

**1. Install the Remote Lab client** alongside the Worker SDK:

```bash
pip install neops-remote-lab
```

The package ships both the pytest plugin (`remote_lab_fixture`) and the HTTP client (`RemoteLabClient`); pytest discovers the plugin automatically.

**2. Point the client at your Remote Lab Manager**:

```bash
export REMOTE_LAB_URL=http://lab.example.com:8000
```

That's the Remote Lab side. From here on, the Worker SDK owns the testing patterns.

## Where to go next

The Worker SDK's [Remote lab testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/) covers the function-block-test patterns:

- Where to declare `remote_lab_fixture` in the worker test layout
- Fixture-rank ordering across multiple worker test modules
- Multi-vendor patterns when a function block targets several NOSes
- The `reuse_lab=True` switch that collapses queue contention across a function-block test suite

Read it next.

## See also

- **[Pytest fixtures](../20-client/10-pytest-fixtures.md)** — the public API the Worker SDK imports.
- **[Worker SDK → Function blocks](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/)** — the unit of automation work whose tests this fixture serves.
- **[Neops ecosystem](../99-appendix/neops-ecosystem.md)** — how Remote Lab fits with the rest of the platform.
