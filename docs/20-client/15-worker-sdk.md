---
title: With Worker SDK
description: Remote-Lab-side notes for Worker SDK consumers — where to declare fixtures, which topologies fit common function-block tests, multi-vendor patterns. Heavy outbound links to the Worker SDK docs; no duplication.
tags: [reference, client, worker-sdk]
crosslink_defines: []
crosslink_references: []
---

# With Worker SDK

*The [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/) imports `remote_lab_fixture` as a stable public API. This page is the Remote-Lab-side complement to the SDK's [Remote lab testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/) — what to know on the topology and fixture side; the SDK owns the function-block-test patterns.*

!!! info "Two pages, two scopes"
    [The Worker SDK testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/) covers fixture composition, mocking patterns within a function-block test, what `WorkflowContext` looks like during a test run, and the worker test layout. **Read it first.**

    *This page* covers what's specific to Remote Lab — which topologies common function-block tests use, what multi-vendor patterns look like, where to draw the line between Worker SDK responsibility and Remote Lab responsibility.

## Where to declare your fixture

The Worker SDK's testing layout puts shared fixtures in a worker-level `conftest.py`. The `remote_lab_fixture` factory call goes there:

```python title="worker_my_thing/tests/conftest.py"
from neops_remote_lab.testing.fixture import remote_lab_fixture

# One topology, shared across every function-block test in this worker.
shared_topo = remote_lab_fixture(
    "tests/topologies/two_router_frr.yml",
    reuse_lab=True,
)
```

Each function-block test then requests `shared_topo` like any pytest fixture. **Do not declare two `remote_lab_fixture`s in the same test** — collection fails with `ValueError`. (See [Invariants → One `remote_lab_fixture` per test](../50-contributing/20-invariants.md#one-remote_lab_fixture-per-test-collection-time).)

For the worker test layout itself, see the [Worker SDK testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/).

## Picking a topology for the function block

Function blocks target real device behaviour. The vendor matters:

- **[Function blocks](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/) that read or push routing config** — FRR is fine and fastest.
- **Function blocks that parse vendor-specific CLI output** (Cisco show-output formats, Junos config blocks) — Cisco IOL or Juniper vSRX. License required.
- **Function blocks driving YANG / gNMI** — Nokia SR Linux. Free under EULA; container-only.

For the decision tree, see [Topology format → Vendor defaults](../10-concepts/40-topology-format.md#vendor-defaults-which-device-to-use). For per-vendor install walkthroughs, see [Vendor setup](../40-deployment/20-vendor-setup.md).

## Multi-vendor function-block tests

When a function block targets several NOSes, declare one fixture per NOS and write parameterised tests:

```python title="worker_my_thing/tests/conftest.py"
frr_topo = remote_lab_fixture("tests/topologies/two_router_frr.yml", reuse_lab=True)
srlinux_topo = remote_lab_fixture(
    "tests/topologies/multi_vendor_frr_srlinux.yml",
    reuse_lab=True,
)
```

Two fixtures across the suite is fine — each test still requests **only one**. Tests against `frr_topo` and tests against `srlinux_topo` get reordered into contiguous blocks; each lab boots once.

For the multi-vendor topology shape itself, see [Cookbook → Multi-vendor (FRR + SR Linux)](../99-appendix/cookbook.md#topology-recipes).

## What this fixture does *not* do

A few things you might expect from a Worker SDK angle that live elsewhere:

- **It does not register your function block.** That's the SDK's `WorkerContext` setup; see [Worker SDK → Worker setup](https://docs.neops.io/neops-worker-sdk-py/docs/).
- **It does not provide a `WorkflowContext`.** That's a workflow-engine concept ([Context](https://docs.neops.io/neops-workflow-engine/docs/10-concepts/30-context/)), unrelated to lab provisioning.
- **It does not mock device responses.** It gives you a real device. If you need to mock, that's a different layer (the SDK's mocking utilities or pytest's `monkeypatch`).
- **It does not run alongside the workflow engine.** Remote Lab is the test substrate — function-block tests use it directly; a deployed workflow at runtime does not.

For where Remote Lab does and doesn't fit in the wider neops platform, see [Neops ecosystem](../99-appendix/neops-ecosystem.md).

## See also

- **[Worker SDK → Remote lab testing](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/)** — the canonical integration guide. Read it next.
- **[Worker SDK → Function blocks](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/)** — what the SDK puts on top of `remote_lab_fixture`.
- **[Pytest fixtures](10-pytest-fixtures.md)** — the full fixture API the SDK imports.
- **[Plug into Worker SDK](../getting-started/15-worker-sdk.md)** — the two-step quickstart.
- **[Cookbook](../99-appendix/cookbook.md)** — runnable topology and Python recipes.
- **[Neops ecosystem](../99-appendix/neops-ecosystem.md)** — peer-project terminology bridge.
