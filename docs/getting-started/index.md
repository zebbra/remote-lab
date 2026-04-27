---
title: Getting Started
description: Install the client, point it at a Remote Lab Manager, and run your first lab-backed pytest — pick the path that matches what runs your tests.
tags: [tutorial, testing]
crosslink_defines: []
crosslink_references: []
---

# Getting Started

## Pick a path

Answer one question: **what runs your tests today?**

- **Pytest, against a Remote Lab Manager you can already reach** → [Quickstart](10-quickstart.md). Ten minutes, three lines of test code.
- **Pytest, but you don't have a server to point at** → [Local development server](20-local-server.md), then return to [Quickstart](10-quickstart.md) from step 3.
- **Anything else — Go, Robot Framework, shell, your own harness** → [REST quickstart](30-rest-quickstart.md). Six cURL calls end-to-end; no Python required.
- **You're wiring this into CI** → [CI quickstart](40-ci-quickstart.md). Env vars, runner pipeline tabs, queue tuning.
- **You operate the lab host (not just consume it)** → skip Getting Started. Start at [Netlab host setup](../40-deployment/10-netlab-host-setup.md).

## In this section

| Guide | What you'll learn |
|---|---|
| [Quickstart](10-quickstart.md) | Install `neops-remote-lab`, set `REMOTE_LAB_URL`, write a minimal topology, declare a `remote_lab_fixture`, and run pytest against a real lab. |
| [Local development server](20-local-server.md) | Don't have a remote VM yet? Install the prerequisites on Ubuntu, run the server on `localhost:8000`, point your tests at it. |
| [REST quickstart](30-rest-quickstart.md) | Drive the lab end-to-end with cURL — six calls, any HTTP-capable stack. The pytest fixture and Python client wrap exactly this lifecycle. |
| [CI quickstart](40-ci-quickstart.md) | Wire the lab into GitHub Actions, GitLab CI, or Jenkins — env-var setup, runner pipeline tabs, VPN connectivity, queue-tuning pointers. |

## What to read next

- **[Pytest Fixtures](../20-client/10-pytest-fixtures.md)** — the stable public API in full: factory arguments, the `remote_lab_client` session fixture, the one-fixture-per-test rule.
- **[Architecture](../10-concepts/10-architecture.md)** — how the server, `LabManager`, and client cooperate; useful before you start debugging queue or lifecycle behaviour.
- **[Topology Format](../10-concepts/40-topology-format.md)** — the `.yml`/`.yaml` extension rule and the `extra_files` multipart contract.
- **[Cookbook](../99-appendix/cookbook.md)** — runnable examples for pytest, Python, cURL, topologies, and deployment.

If you are standing up a **production** Remote Lab Manager host (not just a local dev server), start instead with [Netlab host setup](../40-deployment/10-netlab-host-setup.md) and [Headscale VPN — Quick setup](../40-deployment/20-headscale-quick-setup.md).
