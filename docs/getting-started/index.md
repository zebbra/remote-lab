---
title: Getting Started
description: Install the client, point it at a Remote Lab Manager, and run your first lab-backed pytest.
tags: [tutorial, testing]
crosslink_defines: []
crosslink_references: []
---

# Getting Started

If you are here to get a [function-block](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/)
test passing against a real Netlab topology — on your laptop, in CI, or
both — you are in the right place. The [Quickstart](10-quickstart.md)
walks you from a fresh environment to a passing test in about ten
minutes.

## In this section

| Guide | What you'll learn |
|---|---|
| [Quickstart](10-quickstart.md) | Install `neops-remote-lab`, set `REMOTE_LAB_URL`, write a minimal topology, declare a `remote_lab_fixture`, and run pytest against a real lab. The Python-first onramp; if you're driving from another stack, see the REST quickstart below. |
| [Local development server](20-local-server.md) | Don't have a remote VM yet? Install the prerequisites on Ubuntu, run the server on `localhost:8000`, and point your tests at it. The on-ramp for OSS readers and zebbra-internal devs alike. |
| [REST quickstart](30-rest-quickstart.md) | Drive the lab end-to-end with cURL — create a session, upload a topology, inspect devices, release. The cURL-first onramp for any HTTP-capable stack. The pytest fixture and Python client wrap exactly this lifecycle. |

## What to read next

- **[Pytest Fixtures](../20-client/10-pytest-fixtures.md)** — the stable
  public API in full: factory arguments, the `remote_lab_client`
  session fixture, the one-fixture-per-test rule.
- **[Architecture](../10-concepts/10-architecture.md)** — how the server,
  `LabManager`, and client cooperate; useful before you start debugging
  queue or lifecycle behaviour.
- **[Topology Format](../10-concepts/40-topology-format.md)** — the
  `.yml` extension rule and the `extra_files` multipart contract.

If you are standing up a **production** Remote Lab Manager host (not just
a local dev server), start instead with
[Netlab host setup](../40-deployment/10-netlab-host-setup.md) and
[Headscale VPN](../40-deployment/20-headscale-quick-setup.md).
