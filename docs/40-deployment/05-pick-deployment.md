---
title: Pick a deployment
description: Decision tree for the four deployment shapes — local laptop, single shared VM, multi-tenant lab, CI runner pool. Routes you to the right starting point so you don't read the wrong guide.
tags: [how-to, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Pick a deployment

*Four scenarios, four starting points. Pick the row that matches what you're standing up; each routes into the right guide.*

| Scenario | Path | Setup time |
|---|---|---|
| **Local laptop dev** — one developer, no shared lab, no enclosure | [Run locally](../getting-started/20-local.md) | ~10 minutes |
| **Single shared VM** (small team) | [Netlab host](10-netlab-host-setup.md) → systemd ([Operator runbook](../30-server/10-administration.md)) → [Headscale quick start](30-headscale-quick-setup.md) | ~1 hour |
| **Multi-tenant lab** (large team / multiple sites) | [Netlab host](10-netlab-host-setup.md) → systemd + reverse proxy → [Headscale reference](40-headscale-reference.md) for ACLs | 2–3 hours |
| **CI runner pool** | [Wire into CI](../getting-started/40-ci.md) → subnet routing for the runners ([Headscale reference](40-headscale-reference.md), or any equivalent VPN) | ~30 minutes once a host exists |

The shared-VM and multi-tenant rows assume the project's recommended Headscale enclosure. **Any equivalent network boundary works** — managed Tailscale, NetBird, ZeroTier, plain WireGuard, internal VLAN with IP allowlists, mTLS at a reverse proxy. See [Network access](25-network-enclosure.md) for the family of options before committing.

## When each shape is the right call

<div class="grid cards" markdown>

-   :material-laptop:{ .lg .middle } &nbsp; **[Local laptop](../getting-started/20-local.md)**

    ---

    *One developer, fast iteration, no shared state.*

    Server runs in your terminal, foreground. Stop it when you stop working. No VPN, no lock recovery, no shared queue. Containerlab is greedy with CPU; offload to a VM when laptop heat or other-people's-tests start to matter.

    [Run locally :material-arrow-right:](../getting-started/20-local.md)

-   :material-server:{ .lg .middle } &nbsp; **[Single shared VM](10-netlab-host-setup.md)**

    ---

    *Small team, one lab host, occasional contention.*

    Single instance under `systemd` on a dedicated VM. **Network enclosure** so the team's laptops and CI runners can reach the lab subnet — Headscale is the path we ship docs for, but any VPN or VLAN works equally well. The default deployment shape; covers everything up to maybe a dozen developers.

    [Netlab host setup :material-arrow-right:](10-netlab-host-setup.md)

-   :material-server-network:{ .lg .middle } &nbsp; **[Multi-tenant lab](40-headscale-reference.md#acl-configuration)**

    ---

    *Multiple teams, sometimes several sites, ACLs needed.*

    Same `systemd`-managed instance, plus reverse proxy (TLS), and **ACLs restricting subnet access by user/tag** (Headscale ACLs in our reference deployment; any equivalent policy plane fits). The lab queue serializes contention; the ACL restricts who can queue at all. **Still one process per host** — the one-server invariant doesn't change.

    [ACL configuration :material-arrow-right:](40-headscale-reference.md#acl-configuration)

-   :material-cog-sync:{ .lg .middle } &nbsp; **[CI runner pool](../getting-started/40-ci.md)**

    ---

    *Automated tests against an existing host.*

    Runners need **subnet-route access to the lab host** (tailnet membership in the Headscale path; equivalent on whichever enclosure you picked) and the four `REMOTE_LAB_*` env vars. Set queue tuning per concurrency. The host itself is one of the three shapes above.

    [Wire into CI :material-arrow-right:](../getting-started/40-ci.md)

</div>

## What's the same regardless

Every deployment shares the load-bearing parts:

- **One server per host.** [Filelock](../50-contributing/20-invariants.md#one-server-instance-per-host) catches a second instance.
- **One lab per host.** [LabManager + GLOBAL_LOCK](../50-contributing/20-invariants.md#one-lab-per-host) — Netlab can't run two topologies anyway.
- **`X-Session-ID` is the only access boundary.** [Security model](../30-server/30-security.md). VPN is mandatory; the service has no HTTP authentication.
- **Topology identity is the SHA-256 of file content.** [Lab lifecycle](../10-concepts/30-lab-lifecycle.md#topology-identity-is-content-not-filename). Reuse just works across copy-pasted topologies.

## What changes between shapes

| Concern | Local | Single VM | Multi-tenant | CI pool |
|---|---|---|---|---|
| Process supervisor | foreground | `systemd` | `systemd` + reverse proxy | n/a (uses an existing host) |
| Network enclosure | none | VPN or VLAN (Headscale recommended) | VPN + ACLs + TLS (Headscale recommended) | enclosure-specific auth per runner |
| Lock recovery | `Ctrl+C` and restart | [Stale-lock procedure](../30-server/10-administration.md#stale-lock-recovery) | same, plus monitoring | n/a |
| Vendor images | whatever you need locally | the team's defaults | per-tenant defaults possible | inherits from host |
| Concurrency tuning | n/a | client `REMOTE_LAB_SESSION_TIMEOUT` | server `_WAITING_SESSION_TIMEOUT` matters | [Queue contention math](../10-concepts/20-session-queue.md#queue-contention-under-ci-load) |

## See also

- **[Netlab host](10-netlab-host-setup.md)** — install Netlab + Containerlab rootless. Prerequisite for every deployment except "Local laptop" running on a dev's machine.
- **[Vendor setup](20-vendor-setup.md)** — pick the device images you'll boot (FRR, SR Linux, Cisco IOL, …).
- **[Network access](25-network-enclosure.md)** — the family of network boundary options. Read this if you're not committed to Headscale.
- **[Headscale quick start](30-headscale-quick-setup.md)** — five-command Headscale + Headplane setup, the opinionated path.
- **[Headscale reference](40-headscale-reference.md)** — ACLs, OIDC, troubleshooting (Headscale-specific).
- **[Operator runbook](../30-server/10-administration.md)** — install via uv/pipx, run under `systemd`, recover from stale locks.
- **[Security model](../30-server/30-security.md)** — what the X-Session-ID gate protects against and what it doesn't.
- **[Wire into CI](../getting-started/40-ci.md)** — runner pipeline shapes and queue-tuning pointers.

Next: **[Run the service →](../30-server/index.md)** once you've worked through the install path your shape requires.
