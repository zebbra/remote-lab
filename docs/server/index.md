---
title: Server
description: Operator-facing reference — the HTTP surface, every runtime knob, and the runbook for keeping the server healthy.
tags: [reference, server, operator]
crosslink_defines: []
crosslink_references: []
---

# Server

Everything you need to understand, configure, and run the Remote Lab
Manager service. The three pages below move from contract (REST API)
through knobs (Configuration) to runbook (Administration).

## In this section

| Guide | What you'll learn |
|---|---|
| [REST API](10-rest-api.md) | Every endpoint the service exposes: request schema, response DTOs, error codes, the `X-Session-ID` contract, and end-to-end cURL walkthroughs. |
| [Configuration](20-configuration.md) | Client environment variables, the one server environment variable (`NEOPS_NETLAB_STREAM_OUTPUT`), server CLI flags, and the defaults you should almost never change. |
| [Administration](30-administration.md) | Install via `pipx`, run under `systemd`, recover a stale filelock, handle a stuck lab, and the security posture you sign up for (the service has no authentication). |

## What to read next

- **[Architecture](../concepts/10-architecture.md)** — why the service
  is shaped the way it is; the three cooperating components; the
  one-server-per-host and one-lab-per-host invariants.
- **[Session Queue](../concepts/20-session-queue.md)** — the FIFO model
  that the `X-Session-ID` access boundary enforces.
- **[Netlab host setup](../deployment/10-netlab-host-setup.md)** — must
  be complete before the server will start; the launcher exits if
  `netlab` is not on `PATH`.
- **[Headscale VPN](../deployment/20-headscale-vpn.md)** — the
  recommended enclosure for the internal-trust HTTP surface.
