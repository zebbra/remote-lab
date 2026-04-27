---
title: Server
description: Operator-facing reference — the HTTP surface, every runtime knob, and the runbook for keeping the server healthy.
tags: [reference, server, operator]
crosslink_defines: []
crosslink_references: []
---

# Server

Everything you need to **understand, configure, and run** the Remote Lab
Manager service. The pages below move from **contract** (REST API)
through **knobs** (Configuration) to **runbook** (Administration), then
out to **CI integration** and **debugging** for the day-to-day surfaces.

## In this section

| Guide | What you'll learn |
|---|---|
| [REST API](10-rest-api.md) | Every endpoint the service exposes: request schema, response DTOs, error codes, the `X-Session-ID` contract, and end-to-end cURL walkthroughs. |
| [Configuration](20-configuration.md) | Client environment variables, the one server environment variable (`NEOPS_NETLAB_STREAM_OUTPUT`), server CLI flags, and the defaults you should almost never change. |
| [Administration](30-administration.md) | Install via `pipx`, run under `systemd`, recover a stale filelock, handle a stuck lab, and the security posture you sign up for (the service has no authentication). |
| [CI integration](40-ci-integration.md) | Pipeline-step examples for GitHub Actions, GitLab CI, and Jenkins. Timeout coordination, queue-contention math, parallelism trade-offs, and VPN-runner notes. The reference for wiring Remote Lab into your existing CI. |
| [Debugging](50-debugging.md) | Quick-reference symptom/cause/fix table; common HTTP error codes; client-log + server-log pattern tables; the `/debug/health` endpoint; stale-state recovery. The page to grep when something breaks. |

## What to read next

- **[Architecture](../10-concepts/10-architecture.md)** — why the service
  is shaped the way it is; the three cooperating components; the
  one-server-per-host and one-lab-per-host invariants.
- **[Session Queue](../10-concepts/20-session-queue.md)** — the FIFO model
  that the `X-Session-ID` access boundary enforces.
- **[Netlab host setup](../40-deployment/10-netlab-host-setup.md)** — must
  be complete before the server will start; the launcher exits if
  `netlab` is not on `PATH`.
- **[Headscale VPN](../40-deployment/20-headscale-vpn.md)** — the
  recommended enclosure for the internal-trust HTTP surface.
