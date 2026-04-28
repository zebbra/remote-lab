---
title: Network access
description: Pick the network boundary around your lab host — self-hosted Headscale, managed mesh VPN services (Tailscale, NetBird, ZeroTier, Twingate), plain WireGuard, network-layer ACLs, or application-layer mTLS. The lab service is unaware of which one you pick.
tags: [how-to, deployment, operator, security]
crosslink_defines: []
crosslink_references: []
---

# Network access

*The lab service ships [without HTTP authentication](../30-server/30-security.md), so the network boundary around the host **is** the security perimeter. Headscale is what this project ships docs for; any equivalent works just as well. **Use whatever your organization already runs well** — the lab service is unaware of which boundary surrounds it.*

## The five families of options at a glance

| | Family | Posture | Pick it when |
|---|---|---|---|
| 1 | **[Self-hosted Headscale](30-headscale-quick-setup.md)** | Strong — identity-scoped subnet routes, encrypted peer-to-peer, OIDC-able | You want full control + OSS, and you can run a control plane |
| 2 | **Managed mesh VPN services** &mdash; [Tailscale](https://tailscale.com/), [NetBird](https://netbird.io/), [ZeroTier](https://zerotier.com/), [Twingate](https://www.twingate.com/), … | Strong — same architecture as #1, operated as SaaS | You want zero ops on the control plane |
| 3 | **Plain WireGuard / OpenVPN** | Mixed — strong crypto, weak operations (no key rotation, no central revocation) | You already run a small WG mesh; ≤ a handful of peers |
| 4 | **Network-layer access controls** &mdash; VLAN, IP allowlist, security groups | Conditional — only as strong as the underlying trust zone | The host is already inside an isolated trust zone you control end-to-end |
| 5 | **Application-layer access controls** &mdash; mTLS, [Cloudflare Access](https://www.cloudflare.com/products/zero-trust/access/) / [Tunnel](https://www.cloudflare.com/products/tunnel/), SSO-aware proxy | Different shape — gates HTTP, not subnet routing | You can manage client certs and only need HTTP-layer access |

**Families 1–2 are the recommended posture.** Family 3 is acceptable for very small, tightly-managed deployments. Families 4–5 are situational — usually layered *with* one of the first three, not instead of them.

!!! warning "Posture caveats for families 3–5"
    -   **Family 3 (Plain WireGuard / OpenVPN)** — symmetric peer keys live on disk and don't rotate automatically. A leaked or stolen `wg0.conf` is full tailnet access until you manually rebuild and redistribute keys. Keep keys high-entropy, store them in a secret manager, plan a rotation cadence.
    -   **Family 4 (Network-layer ACLs)** — protects against attackers *outside* the trust zone, not against compromised peers *inside* it. If your "private network" is shared (corporate datacenter with multiple teams, cloud VPC with multiple tenants, lab on the same VLAN as production servers), an internal compromise reaches the lab. Combine with family 1 or 2 for defense in depth.
    -   **Family 5 (mTLS / proxy)** — mTLS authenticates the *transport*, not the *caller* — a compromised client cert still gets a session. Identity-aware proxies layer identity on top, but the lab service itself still has no authentication, so the proxy is the entire boundary. **Layer it *with* a network boundary, not instead of one.**

## Why a boundary is non-negotiable

`neops-remote-lab` ships with no HTTP authentication: no Bearer-token gate, no OAuth flow, no API keys. `client.py` ships with a `REMOTE_LAB_TOKEN` slot that is commented out — the codebase deliberately leaves authentication to the network layer. The `X-Session-ID` header is *session-scope* (it tells the service which queued caller is the active one *after* a session has been granted) — it is not an access-control credential.

**Whoever can reach the service can request a session and run a topology on the lab host.** The boundary you put around the host is the only thing keeping the public internet (or unauthorized peers on your private network) from doing exactly that. See [Security model](../30-server/30-security.md) for the full threat model and the `do`/`don't` list that applies regardless of boundary choice.

## What the lab service requires from any boundary

Any boundary you pick must give you all four:

1. **Peers reach the lab host's `:8000`** for `POST /session`, `GET /healthz`, etc.
2. **Peers reach the lab subnet** that Containerlab/Netlab brings up — typically `192.168.121.0/24` (libvirt) or `172.20.20.0/24` (Containerlab management bridge), depending on how the host is configured.
3. **The lab host advertises subnet routes** to those peers — either via a *[subnet router](https://tailscale.com/kb/1019/subnets)* agent (overlay VPN) or via the routing table on the underlying network (plain L2/L3).
4. **No public exposure of `:8000`.** Whatever the boundary, the lab service should never be directly reachable from the internet.

These four are universal.

## Host settings that carry over {#host-settings}

The lab host needs two system-level settings whenever **the host itself bridges peers into the lab subnet** — i.e. for families 1–4 above (any subnet-router setup). They're documented as commands on the [Headscale quick start](30-headscale-quick-setup.md#prepare-the-lab-host) page; copy them as-is regardless of which subnet-router tool you actually use.

| Setting | Why | Applies to families |
|---|---|---|
| `{"iptables": false}` in `/etc/docker/daemon.json` | Stops Docker's iptables rules from clobbering the Containerlab bridge — concerns Containerlab, not the VPN | **All five.** Containerlab needs this regardless of how peers reach it. |
| `net.ipv4.ip_forward=1` (sysctl.d drop-in) | Enables the host to forward packets between the boundary interface and the lab bridge — required for subnet routing | Families **1–4**. Family 5 (HTTP-layer proxy) doesn't bridge peers into the subnet, so forwarding isn't required for it specifically. |

Other things that hold true for every family:

-   **Prerequisites.** The host has network egress to peers; peers have network reachability to the boundary endpoint; the lab subnet is routable inside the boundary.
-   **What you must NOT do.** Never expose `:8000` to the public internet. The service has no authentication; the boundary IS the access control. See [Security model → operational guidance](../30-server/30-security.md#operational-guidance) for the full do/don't list.

## Where to go from here

- **[Headscale quick start](30-headscale-quick-setup.md)** — the opinionated five-command path if you've decided on self-hosted Headscale.
- **[Headscale reference](40-headscale-reference.md)** — ACLs, OIDC, system settings, troubleshooting once Headscale is running.
- **[Security model](../30-server/30-security.md)** — what the network boundary is protecting against and what it isn't.
- **[Tailscale subnet router KB](https://tailscale.com/kb/1019/subnets)** — upstream docs on the subnet-routing pattern that applies to Tailscale, Headscale, and most managed mesh VPNs.

Next: **[Run the service →](../30-server/index.md)** once the host has a boundary around it.
