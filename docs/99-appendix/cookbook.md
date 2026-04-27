---
title: Cookbook
description: Discovery surface for the examples that ship with the repo — pytest, Python, cURL, topologies, and deployment artifacts. Every link is a GitHub permalink so the recipe survives docs-site rebuilds.
tags: [reference, appendix, examples]
crosslink_defines: []
crosslink_references: []
---

# Cookbook

Pointers to runnable examples in the repo. Every link goes to GitHub so the recipe works whether or not the docs site has the snippet baked in. The CI step `tests/test_examples.py` parametrises over `examples/`, so every file linked below stays valid as the code evolves.

## Pytest recipes

| Recipe | What it shows | Source |
|---|---|---|
| Quickstart demo | Three-line test against a two-router FRR topology — the smallest working `remote_lab_fixture` example. | [`examples/quickstart/`](https://github.com/zebbra/neops-remote-lab/tree/develop/examples/quickstart) |
| Shared-topology fixture | Multiple tests against one running lab via `reuse_lab=True` — the contention-collapse pattern. | [`examples/pytest_fixtures/`](https://github.com/zebbra/neops-remote-lab/tree/develop/examples/pytest_fixtures) |

## Python (no pytest) recipes

| Recipe | What it shows | Source |
|---|---|---|
| Smoke test | End-to-end `RemoteLabClient` lifecycle: acquire, list devices, release, close. | [`examples/scripts/smoke.py`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/scripts/smoke.py) |
| Context-manager wrapper | A `with`-statement wrapper that guarantees release-on-exception, copy-paste-ready. | [`examples/scripts/contextmanager_wrapper.py`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/scripts/contextmanager_wrapper.py) |

## cURL / shell recipes

| Recipe | What it shows | Source |
|---|---|---|
| End-to-end session | The six-call lifecycle in one bash script — create, wait, acquire, inspect, release, delete. | [`examples/curl/end_to_end_session.sh`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/curl/end_to_end_session.sh) |
| Poll-until-active | A timeout-bounded poll loop that survives queue contention. | [`examples/curl/poll_until_active.sh`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/curl/poll_until_active.sh) |
| Force-cleanup | Operator script: take the lab down via `DELETE /lab?force=true` using any ACTIVE session. | [`examples/scripts/force_cleanup.sh`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/scripts/force_cleanup.sh) |

## Topology recipes

| Recipe | What it shows | Source |
|---|---|---|
| Minimal FRR | Two FRR routers, one link — fastest possible boot, the default for CI. | [`examples/topologies/minimal_frr.yml`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/topologies/minimal_frr.yml) |
| Minimal SR Linux | Two-spine, two-leaf SR Linux fabric — the smallest Nokia-NOS example. | [`examples/topologies/minimal_srlinux.yml`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/topologies/minimal_srlinux.yml) |
| Multi-vendor (FRR + SR Linux) | Per-node `device:` selection: an SR Linux spine with two FRR leaves. | [`examples/topologies/multi_vendor_frr_srlinux.yml`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/topologies/multi_vendor_frr_srlinux.yml) |

## Deployment artifacts

| Artifact | What it is | Source |
|---|---|---|
| systemd unit | Drop-in `neops-remote-lab.service` for running the server under systemd. | [`examples/systemd/neops-remote-lab.service`](https://github.com/zebbra/neops-remote-lab/blob/develop/examples/systemd/neops-remote-lab.service) |

## Wanted

Recipes that don't exist yet but would help. Open a PR if you have a good one:

- **Complete GitHub Actions workflow file** as a runnable artifact. The [CI quickstart](../getting-started/40-ci.md) shows the env-var block; a full workflow with checkout, setup, retry policy, and timeout coordination would be more directly useful.
- **Advanced shared-topology pytest pattern** demonstrating fixture-rank ordering across multiple test modules. The current example covers one module; a multi-module example would clarify how the ordering plugin reorders across files.

## How CI keeps these honest

`tests/test_examples.py` parametrises over `examples/topologies/*.{yml,yaml}` and over the runnable scripts, so a recipe that breaks API gets a red CI on the same PR. The `examples/README.md` file documents the convention. Treat the recipes as part of the public surface — change them when the API changes, not after.

## See also

- **[Pytest Fixtures](../20-client/10-pytest-fixtures.md)** — the API the pytest recipes consume.
- **[Python Client](../20-client/20-python-client.md)** — the API the Python (no-pytest) recipes consume.
- **[REST quickstart](../getting-started/30-curl.md)** — the cURL recipes are alternate entry points to the same six-call lifecycle this page narrates.
- **[Topology Format](../10-concepts/40-topology-format.md)** — the YAML shape the topology recipes follow.
- **[Vendor setup](../40-deployment/40-vendor-setup.md)** — the per-vendor install walkthroughs the topology recipes assume.
