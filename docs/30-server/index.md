---
title: Run the Service
description: Operator-facing reference — start the service, run it as a system service, configure it, secure it, look up the REST contract, and debug failures.
tags: [reference, server, operator]
crosslink_defines: []
crosslink_references: []
---

# Run the service

*Everything to start, configure, secure, and operate the Remote Lab Manager. The pages below go from* **easiest** *(start it once, foreground, confirm healthz)* — *through* **runbook** *(install, systemd, lock recovery)*, **knobs**, **security** — *to the* **REST contract** *(reference)* *and* **debugging** *(when something breaks).*

## In this section

<div class="grid cards" markdown>

-   :material-rocket-launch:{ .lg .middle } &nbsp; **[Start it](05-start.md)**

    ---

    Thirty seconds. Foreground launch + healthz check. Every other page in this section assumes you've done this once.

-   :material-account-cog:{ .lg .middle } &nbsp; **[Operator runbook](10-administration.md)**

    ---

    Install via uv/pipx, run under `systemd`, recover from a stale filelock, unstick a wedged lab.

-   :material-tune:{ .lg .middle } &nbsp; **[Server config](20-configuration.md)**

    ---

    CLI flags (`--host`, `--port`, `--debug`, `--log-level`, `--log-config`) and the `NEOPS_NETLAB_STREAM_OUTPUT` env var. Client config lives under [Use from Python](../20-client/30-configuration.md).

-   :material-shield-lock:{ .lg .middle } &nbsp; **[Security model](30-security.md)**

    ---

    What the X-Session-ID gate does and doesn't protect against; the do/don't operational guidance; controls to layer on if you must expose the service.

-   :material-api:{ .lg .middle } &nbsp; **[REST API](40-rest-api.md)**

    ---

    Endpoint-by-endpoint contract: schema, error codes, the `X-Session-ID` matrix, and a cURL example for each.

-   :material-bug:{ .lg .middle } &nbsp; **[Debugging](50-debugging.md)**

    ---

    Symptom/cause/fix table, common HTTP error codes, client and server log patterns, the `/debug/health` endpoint, stale-state recovery. The page to grep when something breaks.

</div>

## What to read next

- **[Architecture](../10-concepts/10-architecture.md)** — why the service is shaped the way it is; the three cooperating components; the one-server-per-host and one-lab-per-host invariants.
- **[Session queue](../10-concepts/20-session-queue.md)** — the FIFO model that the `X-Session-ID` access boundary enforces.
- **[Netlab host setup](../40-deployment/10-netlab-host-setup.md)** — must be complete before the server will start; the launcher exits if `netlab` is not on `PATH`.
- **[VPN: quick setup](../40-deployment/20-headscale-quick-setup.md)** — the recommended enclosure for the internal-trust HTTP surface.
- **[Wire into CI](../getting-started/40-ci.md)** — wire the service into GitHub Actions, GitLab CI, or Jenkins.
