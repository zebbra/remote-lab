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
| **Local laptop dev** — one developer, no shared lab, no VPN | [Run locally](../getting-started/20-local.md) | ~10 minutes |
| **Single shared VM** (small team) | [Netlab host](10-netlab-host-setup.md) → systemd ([Operator runbook](../30-server/10-administration.md)) → [VPN: quick setup](20-headscale-quick-setup.md) | ~1 hour |
| **Multi-tenant lab** (large team / multiple sites) | [Netlab host](10-netlab-host-setup.md) → systemd + reverse proxy → [VPN: reference](30-headscale-reference.md) for ACLs | 2–3 hours |
| **CI runner pool** | [Wire into CI](../getting-started/40-ci.md) → Headscale subnet routing for the runners ([VPN: reference](30-headscale-reference.md)) | ~30 minutes once a host exists |

## When each shape is the right call

<div class="grid cards" markdown>

-   :material-laptop:{ .lg .middle } &nbsp; **Local laptop**

    ---

    *One developer, fast iteration, no shared state.*

    Server runs in your terminal, foreground. Stop it when you stop working. No VPN, no lock recovery, no shared queue. Containerlab is greedy with CPU; offload to a VM when laptop heat or other-people's-tests start to matter.

-   :material-server:{ .lg .middle } &nbsp; **Single shared VM**

    ---

    *Small team, one lab host, occasional contention.*

    Single instance under `systemd` on a dedicated VM. Headscale tailnet so the team's laptops and CI runners can reach the lab subnet. The default deployment shape; covers everything up to maybe a dozen developers.

-   :material-server-network:{ .lg .middle } &nbsp; **Multi-tenant lab**

    ---

    *Multiple teams, sometimes several sites, ACLs needed.*

    Same `systemd`-managed instance, plus reverse proxy (TLS), Headscale ACLs restricting subnet access by user/tag. The lab queue serializes contention; ACL restricts who can queue at all. **Still one process per host** — the one-server invariant doesn't change.

-   :material-cog-sync:{ .lg .middle } &nbsp; **CI runner pool**

    ---

    *Automated tests against an existing host.*

    Runners need tailnet access (subnet routing approved) and the four `REMOTE_LAB_*` env vars. Set queue tuning per concurrency. The host itself is one of the three shapes above.

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
| Network enclosure | none | Headscale tailnet | Headscale + ACLs + TLS | tailnet auth-key per runner |
| Lock recovery | `Ctrl+C` and restart | [Stale-lock procedure](../30-server/10-administration.md#stale-lock-recovery) | same, plus monitoring | n/a |
| Vendor images | whatever you need locally | the team's defaults | per-tenant defaults possible | inherits from host |
| Concurrency tuning | n/a | client `REMOTE_LAB_SESSION_TIMEOUT` | server `_WAITING_SESSION_TIMEOUT` matters | [Queue contention math](../10-concepts/20-session-queue.md#queue-contention-under-ci-load) |

## See also

- **[Netlab host](10-netlab-host-setup.md)** — install Netlab + Containerlab rootless. Prerequisite for every deployment except "Local laptop" running on a dev's machine.
- **[VPN: quick setup](20-headscale-quick-setup.md)** — five-command Headscale + Headplane setup.
- **[VPN: reference](30-headscale-reference.md)** — ACLs, OIDC, troubleshooting.
- **[Operator runbook](../30-server/10-administration.md)** — install via uv/pipx, run under `systemd`, recover from stale locks.
- **[Security model](../30-server/30-security.md)** — what the X-Session-ID gate protects against and what it doesn't.
- **[Wire into CI](../getting-started/40-ci.md)** — runner pipeline shapes and queue-tuning pointers.
