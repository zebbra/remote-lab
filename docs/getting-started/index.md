---
title: Getting Started
description: Install the client, point it at a Remote Lab Manager, and run your first lab-backed pytest — pick the path that matches what runs your tests.
tags: [tutorial, testing]
crosslink_defines: []
crosslink_references: []
---

# Getting Started

*Five paths, pick one. Each routes you to a passing test, a running server, or both — without reading every page first.*

## Pick a path

Answer one question: **what runs your tests today?**

- **Pytest, against a Remote Lab Manager you can already reach** → [Run your first test](10-pytest.md). Ten minutes, three lines of test code.
- **You're a Neops dev using the Worker SDK** → [Plug into Worker SDK](15-worker-sdk.md). Two-step setup, then the Worker SDK testing guide takes over.
- **Pytest, but you don't have a server to point at** → [Run locally](20-local.md), then return to [Run your first test](10-pytest.md) from step 3.
- **Anything else — Go, Robot Framework, shell, your own harness** → [Drive from cURL](30-curl.md). Six cURL calls end-to-end; no Python required.
- **You're wiring this into CI** → [Wire into CI](40-ci.md). Env vars, runner pipeline tabs, queue tuning.
- **You operate the lab host (not just consume it)** → skip Get started. Begin at [Netlab host setup](../40-deployment/10-netlab-host-setup.md).

## In this section

<div class="grid cards" markdown>

-   :material-test-tube:{ .lg .middle } &nbsp; **[Run your first test](10-pytest.md)**

    ---

    Install `neops-remote-lab`, set `REMOTE_LAB_URL`, write a minimal topology, declare a `remote_lab_fixture`, run pytest. Ten minutes, three lines of test code.

-   :material-puzzle:{ .lg .middle } &nbsp; **[Plug into Worker SDK](15-worker-sdk.md)**

    ---

    For Neops dev teams using the Worker SDK. Two-step setup, then the Worker SDK [testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/) takes over with function-block-test patterns.

-   :material-laptop:{ .lg .middle } &nbsp; **[Run locally](20-local.md)**

    ---

    Don't have a remote VM yet? Install Netlab + Containerlab rootless on Ubuntu and run the server on `localhost:8000`. Point your tests at it; resume the test guide.

-   :material-bash:{ .lg .middle } &nbsp; **[Drive from cURL](30-curl.md)**

    ---

    Drive the lab end-to-end with cURL — six calls, any HTTP-capable stack. The pytest fixture and Python client wrap exactly this lifecycle.

-   :material-cog-sync:{ .lg .middle } &nbsp; **[Wire into CI](40-ci.md)**

    ---

    Wire the lab into GitHub Actions, GitLab CI, or Jenkins — env-var setup, runner pipeline tabs, VPN connectivity, queue-tuning pointers.

</div>

## What to read next

- **[Pytest Fixtures](../20-client/10-pytest-fixtures.md)** — the stable public API in full: factory arguments, the `remote_lab_client` session fixture, the one-fixture-per-test rule.
- **[Architecture](../10-concepts/10-architecture.md)** — how the server, `LabManager`, and client cooperate; useful before you start debugging queue or lifecycle behaviour.
- **[Topology Format](../10-concepts/40-topology-format.md)** — the `.yml`/`.yaml` extension rule and the `extra_files` multipart contract.
- **[Cookbook](../99-appendix/cookbook.md)** — runnable examples for pytest, Python, cURL, topologies, and deployment.

If you are standing up a **production** Remote Lab Manager host (not just a local dev server), start instead with [Netlab host setup](../40-deployment/10-netlab-host-setup.md) and [Headscale: quick](../40-deployment/20-headscale-quick-setup.md) (the recommended network enclosure — that page also covers alternatives).
