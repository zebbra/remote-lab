---
title: Deployment
description: Stand up the lab host plus the VPN enclosure around it — Netlab + Containerlab installation, Headscale + Headplane with Docker Compose, and client enrollment.
tags: [how-to, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Deployment

Two bring-up guides cover a fresh Remote Lab host end-to-end: install
and configure rootless Netlab + Containerlab, then enclose the host in
a self-hosted Headscale tailnet so clients and CI can reach lab subnets
without exposing the server.

Follow them in order — the Netlab side boots the actual labs; the
Headscale side gives you the private reachability the Remote Lab
Manager's `X-Session-ID`-only access boundary relies on for safety.

## In this section

| Guide | What you'll learn |
|---|---|
| [Netlab host setup](10-netlab-host-setup.md) | Install `networklab` via `pipx` on Ubuntu 24.04+, configure rootless Containerlab with `clab_admins` + setuid, stop netlab from wrapping Containerlab in `sudo`, enable VRF for FRR labs, and validate with `netlab test clab`. Optional: pre-built Cisco IOL images from the zebbra registry. |
| [Headscale VPN](20-headscale-vpn.md) | Deploy Headscale + Headplane with Docker Compose, authenticate the UI without OIDC, manage users and pre-auth keys, enrol the Remote Lab host as a subnet router, and connect peers with `tailscale up --accept-routes`. Covers HTTP-only testing (`cookie_secure=false`, `TS_ALLOW_INSECURE=1`) and when to move to TLS. |

## What to read next

- **[Administration](../server/30-administration.md)** — install the
  `neops-remote-lab` service itself once the host is ready, including
  the recommended `systemd` unit and the stale-lock recovery runbook.
- **[Configuration](../server/20-configuration.md)** — server CLI flags
  (`--host`, `--port`, `--debug`) and client environment variables.
- **[REST API](../server/10-rest-api.md)** — the HTTP surface now
  protected by the tailnet.
