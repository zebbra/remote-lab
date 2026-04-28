---
title: Deploy & Operate
description: Stand up the lab host plus the VPN enclosure around it — Netlab + Containerlab installation, Headscale + Headplane with Docker Compose, and client enrollment.
tags: [how-to, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Deploy & Operate

*Stand up the lab host plus a network enclosure around it. Three install guides plus a vendor-image walkthrough; pick the path that matches your scale.*

Three bring-up guides cover a fresh Remote Lab host end-to-end: install
and configure rootless [Netlab](https://netlab.tools/) +
[Containerlab](https://containerlab.dev/), enclose the host in a
network boundary so clients and CI can reach lab subnets without
exposing the server, and decide which router/switch images to ship.

The VPN guides walk **one opinionated path** — self-hosted
[Headscale](https://headscale.net/) + [Headplane](https://github.com/tale/headplane) —
because that's what the project's reference deployment uses. Any
equivalent enclosure works (managed Tailscale, WireGuard, IP allowlists,
mTLS at a reverse proxy); see
[Other approaches](20-headscale-quick-setup.md#other-approaches) on the
quick-setup page for when each fits.

Follow the install guides in order — the Netlab side boots the actual
labs; the network side gives you the private reachability the Remote
Lab Manager's `X-Session-ID`-only access boundary relies on for safety.
The vendor page is reference material you can hop into any time you need
to add a new device kind.

## In this section

<div class="grid cards" markdown>

-   :material-map-marker-path:{ .lg .middle } &nbsp; **[Pick a deployment](05-pick-deployment.md)**

    ---

    Decision tree for the four deployment shapes — local laptop, single shared VM, multi-tenant lab, CI runner pool. Routes you to the right starting point.

-   :material-server-network:{ .lg .middle } &nbsp; **[Netlab host](10-netlab-host-setup.md)**

    ---

    Install `networklab` on Ubuntu 24.04+, configure rootless Containerlab with `clab_admins` + setuid, stop netlab from wrapping Containerlab in `sudo`, validate with `netlab test clab`.

-   :material-shield-lock:{ .lg .middle } &nbsp; **[Headscale: quick](20-headscale-quick-setup.md)**

    ---

    Five-command happy path through the project's recommended enclosure — [Headscale](https://headscale.net/) + [Headplane](https://github.com/tale/headplane) via Docker Compose, the lab host as a subnet router, one client peer reaching the lab subnet. **Alternatives in the page's [Other approaches](20-headscale-quick-setup.md#other-approaches) section.**

-   :material-network-pos:{ .lg .middle } &nbsp; **[Headscale reference](30-headscale-reference.md)**

    ---

    Configuration surface for a deployed Headscale tailnet — ACL configuration, user and pre-auth key management, system settings, troubleshooting, and the full command summary.

-   :material-router-network:{ .lg .middle } &nbsp; **[Vendor setup](40-vendor-setup.md)**

    ---

    Per-vendor install walkthroughs — FRR auto-pull, Nokia SR Linux image pin, Cisco IOL [vrnetlab](https://github.com/hellt/vrnetlab) build. Decision tree lives in [Topology format](../10-concepts/40-topology-format.md#vendor-defaults-which-device-to-use).

</div>

## What to read next

- **[Operator runbook](../30-server/10-administration.md)** — install the
  `neops-remote-lab` service itself once the host is ready, including
  the recommended `systemd` unit and the stale-lock recovery runbook.
- **[Configuration](../30-server/20-configuration.md)** — server CLI flags
  (`--host`, `--port`, `--debug`) and client environment variables.
- **[REST API](../30-server/40-rest-api.md)** — the HTTP surface now
  protected by the tailnet.
