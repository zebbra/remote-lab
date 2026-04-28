---
title: Cookbook
description: Runnable examples that ship with the repo — pytest, Python, cURL, topologies, deployment artifacts. Each recipe expands inline; CI keeps every file honest.
tags: [reference, appendix, examples]
crosslink_defines: []
crosslink_references: []
---

# Cookbook

*Every recipe below ships in the repo, expands inline, and is tested by CI. Click "View source" to see the full file; copy-paste it; the GitHub permalink at the bottom of each block lets you bookmark or link to it.*

`tests/test_examples.py` parametrises over `examples/` — when an API change breaks an example, the same PR sees red CI. Treat the recipes as part of the public surface.

## Pytest recipes

### Quickstart demo

The smallest working `remote_lab_fixture` example — three-line test against a two-router FRR topology.

??? example "View `examples/quickstart/conftest.py`"

    ```python title="examples/quickstart/conftest.py"
    --8<-- "../examples/quickstart/conftest.py"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/quickstart/conftest.py)

??? example "View `examples/quickstart/test_demo.py`"

    ```python title="examples/quickstart/test_demo.py"
    --8<-- "../examples/quickstart/test_demo.py"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/quickstart/test_demo.py)

??? example "View `examples/quickstart/demo.yml`"

    ```yaml title="examples/quickstart/demo.yml"
    --8<-- "../examples/quickstart/demo.yml"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/quickstart/demo.yml)

### Shared-topology fixture

Multiple tests against one running lab via `reuse_lab=True` — the contention-collapse pattern.

??? example "View `examples/pytest_fixtures/conftest.py`"

    ```python title="examples/pytest_fixtures/conftest.py"
    --8<-- "../examples/pytest_fixtures/conftest.py"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/pytest_fixtures/conftest.py)

??? example "View `examples/pytest_fixtures/test_frr_ospf.py`"

    ```python title="examples/pytest_fixtures/test_frr_ospf.py"
    --8<-- "../examples/pytest_fixtures/test_frr_ospf.py"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/pytest_fixtures/test_frr_ospf.py)

## Python (no pytest) recipes

### Smoke test

End-to-end `RemoteLabClient` lifecycle: acquire, list devices, release, close.

??? example "View `examples/scripts/smoke.py`"

    ```python title="examples/scripts/smoke.py"
    --8<-- "../examples/scripts/smoke.py"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/scripts/smoke.py)

### Context-manager wrapper

A `with`-statement wrapper that guarantees `release` on exception. Copy-paste-ready for any non-pytest script.

??? example "View `examples/scripts/contextmanager_wrapper.py`"

    ```python title="examples/scripts/contextmanager_wrapper.py"
    --8<-- "../examples/scripts/contextmanager_wrapper.py"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/scripts/contextmanager_wrapper.py)

## cURL / shell recipes

### End-to-end session

The six-call lifecycle in one bash script — create, wait, acquire, inspect, release, delete.

??? example "View `examples/curl/end_to_end_session.sh`"

    ```bash title="examples/curl/end_to_end_session.sh"
    --8<-- "../examples/curl/end_to_end_session.sh"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/curl/end_to_end_session.sh)

### Poll-until-active

A timeout-bounded poll loop that survives queue contention.

??? example "View `examples/curl/poll_until_active.sh`"

    ```bash title="examples/curl/poll_until_active.sh"
    --8<-- "../examples/curl/poll_until_active.sh"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/curl/poll_until_active.sh)

### Force-cleanup

Operator script: take the lab down via `DELETE /lab?force=true` using any ACTIVE session.

??? example "View `examples/scripts/force_cleanup.sh`"

    ```bash title="examples/scripts/force_cleanup.sh"
    --8<-- "../examples/scripts/force_cleanup.sh"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/scripts/force_cleanup.sh)

## Topology recipes

### Minimal FRR

Two FRR routers, one link — fastest possible boot, the default for CI.

??? example "View `examples/topologies/minimal_frr.yml`"

    ```yaml title="examples/topologies/minimal_frr.yml"
    --8<-- "../examples/topologies/minimal_frr.yml"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/topologies/minimal_frr.yml)

### Minimal SR Linux

Two-spine, two-leaf SR Linux fabric — the smallest Nokia-NOS example.

??? example "View `examples/topologies/minimal_srlinux.yml`"

    ```yaml title="examples/topologies/minimal_srlinux.yml"
    --8<-- "../examples/topologies/minimal_srlinux.yml"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/topologies/minimal_srlinux.yml)

### Multi-vendor (FRR + SR Linux)

Per-node `device:` selection: an SR Linux spine with two FRR leaves. Useful when [Worker SDK function blocks](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/) target both vendors.

??? example "View `examples/topologies/multi_vendor_frr_srlinux.yml`"

    ```yaml title="examples/topologies/multi_vendor_frr_srlinux.yml"
    --8<-- "../examples/topologies/multi_vendor_frr_srlinux.yml"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/topologies/multi_vendor_frr_srlinux.yml)

## Deployment artifacts

### systemd unit

Drop-in `neops-remote-lab.service` for running the server under systemd.

??? example "View `examples/systemd/neops-remote-lab.service`"

    ```ini title="examples/systemd/neops-remote-lab.service"
    --8<-- "../examples/systemd/neops-remote-lab.service"
    ```

    [View on GitHub :material-arrow-right:](https://github.com/zebbra/remote-lab/blob/develop/examples/systemd/neops-remote-lab.service)

## Worker SDK function-block test

For Neops devs using the [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/), the function-block-test pattern lives in the SDK's docs — not in this cookbook. Two-step setup (install + `REMOTE_LAB_URL`) on this side, then read:

- [Plug into Worker SDK](../getting-started/15-worker-sdk.md) — the two-step Remote-Lab-side setup.
- [With Worker SDK](../20-client/15-worker-sdk.md) — Remote-Lab-side notes (where to declare fixtures, multi-vendor patterns).
- [**Worker SDK → Remote lab testing**](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/) — the canonical integration guide.

## Wanted

Recipes that don't exist yet but would help. Open a PR if you have a good one:

- **Complete GitHub Actions workflow file** as a runnable artifact. The [Wire into CI](../getting-started/40-ci.md) page shows the env-var block; a full workflow with checkout, setup, retry policy, and timeout coordination would be more directly useful.
- **Advanced shared-topology pytest pattern** demonstrating fixture-rank ordering across multiple test modules. The current example covers one module; a multi-module example would clarify how the ordering plugin reorders across files.

## How CI keeps these honest

`tests/test_examples.py` parametrises over `examples/topologies/*.{yml,yaml}` and over the runnable scripts. A recipe that breaks the API gets a red CI on the same PR. The `examples/README.md` file documents the convention. Treat the recipes as part of the public surface — change them when the API changes, not after.

## See also

- **[Pytest fixtures](../20-client/10-pytest-fixtures.md)** — the API the pytest recipes consume.
- **[Python client](../20-client/20-python-client.md)** — the API the Python (no-pytest) recipes consume.
- **[Drive from cURL](../getting-started/30-curl.md)** — the cURL recipes are alternate entry points to the same six-call lifecycle.
- **[Topology format](../10-concepts/40-topology-format.md)** — the YAML shape the topology recipes follow.
- **[Vendor setup](../40-deployment/20-vendor-setup.md)** — the per-vendor install walkthroughs the topology recipes assume.
