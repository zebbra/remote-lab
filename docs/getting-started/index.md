---
title: Getting Started
description: Install the client, point it at a Remote Lab Manager, and run your first lab-backed pytest.
tags: [tutorial, testing]
crosslink_defines: []
crosslink_references: []
---

# Getting Started

If you are here to get a function-block test passing against a real
Netlab topology — on your laptop, in CI, or both — you are in the right
place. The [Quickstart](10-quickstart.md) walks you from a fresh
environment to a passing test in about ten minutes.

## In this section

| Guide | What you'll learn |
|---|---|
| [Quickstart](10-quickstart.md) | Install `neops-remote-lab`, set `REMOTE_LAB_URL`, write a minimal topology, declare a `remote_lab_fixture`, and run pytest against a real lab. |

## What to read next

- **[Pytest Fixtures](../client/10-pytest-fixtures.md)** — the stable
  public API in full: factory arguments, the `remote_lab_client`
  session fixture, the one-fixture-per-test rule.
- **[Architecture](../concepts/10-architecture.md)** — how the server,
  `LabManager`, and client cooperate; useful before you start debugging
  queue or lifecycle behaviour.
- **[Topology Format](../concepts/40-topology-format.md)** — the
  `.yml` extension rule and the `extra_files` multipart contract.

If you are standing up the Remote Lab Manager host itself, start instead
with [Netlab host setup](../deployment/10-netlab-host-setup.md) and
[Headscale VPN](../deployment/20-headscale-vpn.md).
