---
title: Deploy & Operate
description: Stand up the lab host plus the VPN enclosure around it — Netlab + Containerlab installation, Headscale + Headplane with Docker Compose, and client enrollment.
tags: [how-to, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Deploy & Operate

Three bring-up guides cover a fresh Remote Lab host end-to-end: install
and configure rootless [Netlab](https://netlab.tools/) +
[Containerlab](https://containerlab.dev/), enclose the host in a
self-hosted [Headscale](https://headscale.net/) tailnet so clients and
CI can reach lab subnets without exposing the server, and decide which
router/switch images to ship.

Follow the install guides in order — the Netlab side boots the actual
labs; the Headscale side gives you the private reachability the Remote
Lab Manager's `X-Session-ID`-only access boundary relies on for safety.
The vendor page is reference material you can hop into any time you need
to add a new device kind.

## In this section

| Guide | What you'll learn |
|---|---|
| [Netlab host setup](10-netlab-host-setup.md) | Install `networklab` on Ubuntu 24.04+, configure rootless Containerlab with `clab_admins` + setuid, stop netlab from wrapping Containerlab in `sudo`, enable VRF for FRR labs, and validate with `netlab test clab`. |
| [Headscale VPN](20-headscale-vpn.md) | Deploy Headscale + Headplane with Docker Compose, authenticate the UI without OIDC, manage users and pre-auth keys, enrol the Remote Lab host as a subnet router, and connect peers with `tailscale up --accept-routes`. Covers HTTP-only testing (`cookie_secure=false`, `TS_ALLOW_INSECURE=1`) and when to move to TLS. |
| [Vendors & images](30-vendor-images.md) | Pick a router/switch image to run inside Netlab — open-source defaults ([FRR](https://netlab.tools/platforms/frr/), [Nokia SR Linux](https://netlab.tools/platforms/srlinux/)), licensed options ([Cisco IOL](https://netlab.tools/platforms/cisco_iol/)), and the recipe for adding any other [Netlab-supported platform](https://netlab.tools/platforms/). Also: FRR limitations to know before you commit. |

## What to read next

- **[Administration](../30-server/30-administration.md)** — install the
  `neops-remote-lab` service itself once the host is ready, including
  the recommended `systemd` unit and the stale-lock recovery runbook.
- **[Configuration](../30-server/20-configuration.md)** — server CLI flags
  (`--host`, `--port`, `--debug`) and client environment variables.
- **[REST API](../30-server/10-rest-api.md)** — the HTTP surface now
  protected by the tailnet.
