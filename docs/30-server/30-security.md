---
title: Security model
description: The full threat model for an internal-trust service — what the X-Session-ID gate does and doesn't protect against, the do/don't operational guidance, and the controls to layer on if you must expose the service.
tags: [reference, server, security, operator]
crosslink_defines: []
crosslink_references: []
---

# Security model

*The threat model for an internal-trust service. **No HTTP authentication.** Every control on this page is a fence around that single fact.*

`neops-remote-lab` ships without bearer-token, OAuth, or mTLS. Every other security control on this page builds on a single fact: the only access boundary on `/lab/*` is the `X-Session-ID` header of an ACTIVE session. Everything else — the VPN enclosure, the firewall rules, the operational guidance — is a fence around that fact.

If you don't have time to read the rest of the page, the short version is: **deploy behind a VPN, treat any caller able to complete the session handshake as authorized, and don't expose port 8000 to anything broader than a known network.**

!!! danger "No HTTP authentication"
    `neops-remote-lab` ships **without** bearer-token, OAuth, or mTLS authentication. The only access boundary on `/lab/*` is the `X-Session-ID` of an ACTIVE session. **Deploy behind a VPN.**

## The only access boundary

<!-- trace: neops_remote_lab/server.py:390 -->
The sole boundary on `/lab/*` and `/session/heartbeat` is the `X-Session-ID` header — and only for a session that is currently in the ACTIVE state in the FIFO queue.

| Caller state | Response on `/lab/*` |
|---|---|
| Unknown session id | `404 Not Found` |
| WAITING (not-yet-ACTIVE) session | `423 Locked` |
| ACTIVE session | request proceeds |

Anyone who can create a session (`POST /session`, no auth) can eventually reach ACTIVE by waiting in the queue.

The asymmetry on `/session/heartbeat` is deliberate: it accepts any session that exists (WAITING or ACTIVE), because a queued client needs to keep its slot alive before promotion. See [Session Queue → access boundary](../10-concepts/20-session-queue.md#the-access-boundary).

## What the `X-Session-ID` gate is not

- **Not an authentication header.** Anyone able to call `POST /session` (which has no auth) gets a fresh session ID. The gate is a contract about queue ordering, not about identity.
- **Not a secret.** It's returned in plaintext by an unauthenticated endpoint. If your network is hostile, the session ID is already compromised.
- **Not transport security.** HTTPS is fine and recommended in front of the service, but TLS by itself doesn't authenticate the *caller* — it authenticates the *server* to the caller and encrypts the bytes between them.

## Operational guidance

| Do | Don't |
|---|---|
| Bind the server behind a network enclosure — VPN ([Headscale](../40-deployment/30-headscale-quick-setup.md) is the recommended one; managed Tailscale, WireGuard, OpenVPN, ZeroTier, etc. all work) or an internal-only VLAN with IP allowlists. | Expose `:8000` to the public internet. |
| Use `--host` to bind to a specific interface when the host has a public NIC. | Leave `--host 0.0.0.0` on a multi-homed host without a firewall. |
| Restrict network reachability with host or cloud firewall rules. | Rely on `X-Session-ID` as a secret — it's returned by an unauthenticated `POST /session`. |
| Use a reverse proxy (nginx, Caddy) with TLS + mutual auth if you must expose across hosts. | Assume HTTPS by itself protects the endpoints — the service still trusts any caller able to complete the session handshake. |

## When you must expose the service

If your deployment requires network reachability beyond a single VPN, layer these controls in front of the server:

1. **Network-level ACLs** — restrict TCP 8000 to known caller subnets. The cheapest possible boundary; deploy this first.
2. **mTLS at a reverse proxy** — each caller presents a client certificate. The proxy authenticates the certificate; the lab service still doesn't.
3. **Rate limiting on `POST /session`** — prevents queue-flooding by a hostile or buggy caller. The service has no defence against this on its own.

None of this replaces the need to treat the service as internal-trust; it reduces the blast radius of a compromised caller.

## What this means for contributors

The "X-Session-ID is the only access boundary" rule is enforced as an [invariant](../50-contributing/20-invariants.md#x-session-id-is-the-only-access-boundary-on-lab). Adding any other auth path (Bearer, mTLS, header magic) without removing this one creates a confused threat model: callers get to choose which boundary to bypass.

If a future requirement demands real auth, the right shape is to *replace* `X-Session-ID` with the new gate, not stack a second one on top.

## See also

- **[Headscale quick start](../40-deployment/30-headscale-quick-setup.md)** — the recommended VPN enclosure in five commands.
- **[Network access](../40-deployment/25-network-enclosure.md)** — the family of alternative boundary options (managed mesh VPN services, plain WireGuard, network-layer ACLs, application-layer mTLS).
- **[REST API](40-rest-api.md)** — the contract table that the gate enforces.
- **[Session Queue](../10-concepts/20-session-queue.md)** — the FIFO state machine ACTIVE-only gating sits on top of.
- **[Invariants → X-Session-ID is the only access boundary](../50-contributing/20-invariants.md#x-session-id-is-the-only-access-boundary-on-lab)** — the rule, in the contributor's voice.
