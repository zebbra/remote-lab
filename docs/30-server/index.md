---
title: Run the Service
description: Operator-facing reference — the HTTP surface, every runtime knob, the security model, and the runbook for keeping the server healthy.
tags: [reference, server, operator]
crosslink_defines: []
crosslink_references: []
---

# Run the Service

Everything to understand, configure, and run the Remote Lab Manager service. The pages move from **contract** (REST API) through **knobs** (Configuration) to **runbook** (Administration), then out to **security** posture and **debugging** for the day-to-day surfaces.

## In this section

| Guide | What you'll learn |
|---|---|
| [REST API](10-rest-api.md) | Every endpoint the service exposes: request schema, response DTOs, error codes, the `X-Session-ID` contract, and end-to-end cURL walkthroughs. |
| [Configuration](20-configuration.md) | Server CLI flags, the one server env var (`NEOPS_NETLAB_STREAM_OUTPUT`), and the defaults you should almost never change. Client config lives under [Use from Python](../20-client/30-configuration.md). |
| [Administration](30-administration.md) | Install via `pipx`, run under `systemd`, recover a stale filelock, handle a stuck lab. |
| [Security model](40-security.md) | What the X-Session-ID gate does and doesn't protect against, the do/don't operational guidance, and the controls to layer on if you must expose the service. |
| [Debugging](50-debugging.md) | Quick-reference symptom/cause/fix table; common HTTP error codes; client-log + server-log pattern tables; the `/debug/health` endpoint; stale-state recovery. The page to grep when something breaks. |

## What to read next

- **[Architecture](../10-concepts/10-architecture.md)** — why the service is shaped the way it is; the three cooperating components; the one-server-per-host and one-lab-per-host invariants.
- **[Session Queue](../10-concepts/20-session-queue.md)** — the FIFO model that the `X-Session-ID` access boundary enforces.
- **[Netlab host setup](../40-deployment/10-netlab-host-setup.md)** — must be complete before the server will start; the launcher exits if `netlab` is not on `PATH`.
- **[Headscale VPN — Quick setup](../40-deployment/20-headscale-quick-setup.md)** — the recommended enclosure for the internal-trust HTTP surface.
- **[CI quickstart](../getting-started/40-ci.md)** — wire the service into GitHub Actions, GitLab CI, or Jenkins.
