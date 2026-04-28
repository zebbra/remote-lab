---
title: Headscale Reference
description: ACL configuration, user and pre-auth key management, system settings, troubleshooting, and the full command summary for a deployed Headscale tailnet.
tags: [reference, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Headscale reference

*Configuration surface for a deployed Headscale tailnet — ACLs, OIDC, system settings, troubleshooting, full command summary.*

!!! info "**Reference for the opinionated path**"
    This page is Headscale-specific — ACL syntax, Headplane configuration, the Compose layout we ship. If you're picking your enclosure and haven't decided yet, start at [Network access](25-network-enclosure.md) for the family of options (managed mesh VPN services, plain WireGuard, network-layer ACLs, application-layer mTLS, …). The lab service is unaware of which one you pick.

For the five-command happy path, see [Headscale quick start](30-headscale-quick-setup.md). This page covers the configuration surface you reach for once the tailnet is running — ACLs, user management, the Compose+config layout, troubleshooting, and a quick command summary.

## Repository layout

The Compose files and configuration in this repo live at the repository root:

```
headscale/
  ├─ docker-compose.yml
  ├─ headplane.config.yaml
  ├─ config/
  │  ├─ config.yaml
  │  ├─ derp.yaml
  │  └─ dns_records.json     # auto-created on first `docker compose up`
  ├─ lib/                    # auto-created: Headscale state (/var/lib/headscale)
  ├─ run/                    # auto-created: Headscale sockets (/var/run/headscale)
  └─ headplane-data/         # auto-created: Headplane data (/var/lib/headplane)
```

### `config/config.yaml` — Headscale configuration

<!-- trace: headscale/config/config.yaml:13 -->
The shipped value of `server_url` is the placeholder `http://CHANGE-ME.example:8080`. You MUST override this to a host or IP your clients can reach — for production, a `https://headscale.example.com` URL behind a reverse proxy with TLS is the recommended shape.

!!! warning "Clients must reach `server_url`"
    A peer that cannot reach the control plane cannot register.

DNS/MagicDNS and DERP settings are present and can be adjusted later.

### `headplane.config.yaml` — Headplane configuration

<!-- trace: headscale/headplane.config.yaml:23 -->
Points to Headscale at `http://headscale:8080` (the Compose service name) and mounts Headscale's `config.yaml` for visibility in the UI. See [Headplane](#headplane) below for what each section does.

### `docker-compose.yml`

<!-- trace: headscale/docker-compose.yml:35 -->

- `headscale`: exposes `8080` and `9090`, bind-mounts `./lib` at `/var/lib/headscale`, `./run` at `/var/run/headscale`, and `./config` at `/etc/headscale`.
- `headplane`: exposes `3000`, bind-mounts `./headplane-data` at `/var/lib/headplane`, mounts the Headscale config for UI introspection.

For a first run you typically only need to change `server_url` in `config/config.yaml` and, if you want Headscale to serve extra DNS records, populate `config/dns_records.json`.

## Reverse proxy + HTTPS + DNS

Use a proper reverse proxy (Nginx, Caddy, Traefik) with HTTPS and a DNS name so `server_url` is a stable, secure URL like `https://headscale.example.com`. Once HTTPS is in front:

- Update `server_url` to the `https://…` URL.
- Set `server.cookie_secure = true` in `headplane.config.yaml`.
- Drop `TS_ALLOW_INSECURE=1` from `tailscale up` invocations.

## User and pre-auth key management

Manage users and pre-auth keys with the Headscale CLI or the [Headplane UI](#headplane-ui-workflows) — both write to the same Headscale state, pick whichever fits your workflow.

Headscale CLI:

```bash
# Create a user (owns machines and pre-auth keys)
docker exec headscale headscale users create <user>

# Create a pre-auth key for that user (valid 24h)
docker exec headscale headscale preauthkeys create -u <user> -e 24h

# Optional flags:
#   --ephemeral   create an ephemeral key (machine disappears when inactive)
#   -r            reusable key (can be used multiple times)
```

Use such a key with `tailscale up --auth-key <key>` to skip interactive approval. The same operations are also available in the [Headplane UI](#headplane-ui-workflows) below if you prefer clicking.

## ACL configuration

Headscale supports ACLs (access-control lists) that restrict which tailnet members can reach which destinations. Configure ACLs in `config/config.yaml` under `acl_policy_path`, pointing at a HuJSON policy file. Reload with:

```bash
docker exec headscale headscale policy check
docker compose restart headscale
```

For the policy file format, see [Headscale ACL docs](https://headscale.net/stable/ref/acls/). At minimum, restrict access to the lab subnet to the users and tags that need it; "default-allow" leaves the lab service exposed to every peer on the tailnet.

## Headplane {#headplane}

[Headplane](https://github.com/tale/headplane) is the web UI on top of Headscale. It runs as a separate container alongside Headscale (see the [Compose layout](#docker-composeyml) above), reads its own configuration from `headplane.config.yaml`, and signs browser sessions with a `cookie_secret` that you generate during initial setup ([Quick start → Configure](30-headscale-quick-setup.md#generate-the-headplane-cookie-secret)).

### Reaching the UI {#reaching-the-ui}

The shipped `docker-compose.yml` binds Headplane on `:3000` and Headscale on `:8080`/`:9090` to **all interfaces** of the host (`0.0.0.0`). On a host with no public NIC, that's effectively the lab's private network. On a host with a public IP, **the UI would be exposed to the internet** — don't run that way. Three patterns for reaching the UI safely:

#### Pattern 1 — SSH tunnel (single operator, simplest) {#ssh-tunnel}

Forward the lab host's `:3000` to your laptop's `:3000` over an existing SSH connection. Your browser hits `http://127.0.0.1:3000` on your laptop and the traffic flows encrypted through SSH into the lab host's loopback. Nothing on the lab host's `:3000` needs to be reachable from your laptop's network for this to work.

```bash
ssh -L 3000:localhost:3000 <user>@$HEADSCALE_HOST
# Then on your laptop, open http://127.0.0.1:3000/admin
```

The `-L 3000:localhost:3000` flag means: "open port 3000 on this side; forward traffic through SSH to `localhost:3000` *on the remote side*". Repeat with `-L 8080:localhost:8080` if you need to reach Headscale's API too (rare — most operations go through the UI or `docker exec`).

**Pick this when:** you're a solo operator setting up the lab; you already have SSH access to the host; you don't want to bind another port or stand up a reverse proxy.

**Trade-offs:** every operator needs SSH access to the host. The tunnel only works while your `ssh` process runs.

#### Pattern 2 — Tailnet IP (after the lab host is registered) {#tailnet-ip-access}

Once you've registered the lab host as a subnet router (the [Register the lab host](30-headscale-quick-setup.md#register-the-lab-host-as-a-subnet-router) step in Quick start) and connected your laptop as a peer, the lab host has a tailnet IP — typically in the `100.64.0.0/10` range. The Headplane UI is reachable at `http://<lab-host-tailnet-ip>:3000/admin` from any peer that has accepted the lab routes.

**Pick this when:** you've finished bootstrapping the tailnet and want a steady-state way to reach the UI from any tailnet peer.

**Trade-offs:** chicken-and-egg during initial setup — you need the SSH tunnel pattern (or direct LAN access) to do the bootstrap *before* the tailnet exists. After that, this is the cleanest path.

#### Pattern 3 — Reverse proxy with HTTPS + OIDC (production) {#reverse-proxy-access}

For a multi-operator or production deployment, put Nginx, Caddy, or Traefik in front of Headplane. The proxy terminates HTTPS, optionally authenticates the caller (mTLS or an SSO-aware proxy like [Cloudflare Access](https://www.cloudflare.com/products/zero-trust/access/)), and forwards to `:3000` on the lab host's loopback. Set `server.cookie_secure = true` in `headplane.config.yaml` and update `public_url` to the HTTPS URL — see [Reverse proxy + HTTPS + DNS](#reverse-proxy-https-dns) above.

**Pick this when:** the host is shared, OIDC is configured, or you want HTTPS for any reason (which you should, eventually).

**Trade-offs:** more moving parts (proxy + cert renewal). The right shape once you outgrow patterns 1 and 2.

### Headplane UI workflows {#headplane-ui-workflows}

Once Headplane is running and you've signed in, the UI exposes:

-   **Machines** — view connected peers, approve route advertisements, remove stale machines.
-   **Users** — create and rename users, browse their machines.
-   **Keys** — generate, list, and expire pre-auth keys (the same surface as `headscale preauthkeys` on the CLI).
-   **Settings** — access the OIDC/SSO configuration if you've turned it on (see below).

Whether you use the UI or the [Headscale CLI](#user-and-pre-auth-key-management) is operator preference; both write to the same Headscale state.

### Authentication

The shipped configuration has **no built-in authentication**: the only barrier to the UI is reaching `:3000`. For a single-operator host that's often acceptable behind an SSH tunnel; for any shared deployment, configure OIDC (next section) before non-operators get tailnet access. See also the Headplane warning in [Quick start → Start the services](30-headscale-quick-setup.md#start-the-services).

### OIDC (optional) {#oidc-optional}

You can wire Headplane up to an OIDC identity provider (Authentik, Keycloak, Auth0, Google Workspace, …) so that user management is backed by your IdP. Examples ship in `headplane.config.yaml`; the upstream [Headplane docs](https://github.com/tale/headplane) cover the full configuration surface.

Pair OIDC with HTTPS (`server.cookie_secure = true` in `headplane.config.yaml`) — see [Reverse proxy + HTTPS + DNS](#reverse-proxy-https-dns).

### Cookie secret hygiene

The shipped `headplane.config.yaml` has a `cookie_secret` placeholder that you replace at install time. The bootstrap command in [Quick start → Configure](30-headscale-quick-setup.md#generate-the-headplane-cookie-secret) writes a random hex value directly into the file — fine for a single-operator host, **not for shared deployments**. For anything shared, store the secret outside the repo (Vault, SOPS-encrypted file, your CI's secrets store) and template it in at deploy time. A leaked secret lets anyone forge admin sessions and rewrite ACLs.

## System settings

| Setting | Why | Scope |
|---|---|---|
| `iptables: false` in `/etc/docker/daemon.json` | Stops Docker's iptables rules from blocking container traffic across the bridged lab network. | Containerlab — applies regardless of VPN choice |
| `net.ipv4.ip_forward=1` (sysctl.d drop-in) | Lets the lab host forward packets between the boundary interface and the lab bridge — required for subnet routing | Any subnet-router setup (Headscale, Tailscale, NetBird, plain WireGuard, internal VLAN) |
| Tailscale `--accept-routes` on peers | Without this, peers ignore advertised subnet routes from the lab host. | Tailscale-protocol clients only (Headscale + managed Tailscale) |

The first two are documented as commands on the [Quick start → Prepare the lab host](30-headscale-quick-setup.md#prepare-the-lab-host) page. The applicability across the five Network access families is summarized in [Network access → Host settings that carry over](25-network-enclosure.md#host-settings).

## DERP

For constrained NATs, consider enabling embedded DERP (requires TLS) or referencing external DERP maps; see comments in `config/config.yaml`.

## Troubleshooting

| Symptom | Check |
|---|---|
| `docker compose up` fails with port in use | `sudo ss -ltnp \| grep -E ':(3000\|8080\|9090)'` — another service owns the port |
| Headplane login spins / 401 loop over HTTP | `server.cookie_secure` in `headplane.config.yaml` is `true`; flip to `false` for plain-HTTP access |
| Tailscale client "cannot reach control-plane" | `$HEADSCALE_HOST` not reachable from the client. Fix DNS/firewall, or forward `:8080` over SSH the same way as [Reaching the UI](#ssh-tunnel) does for `:3000`. |
| Peers approved but lab subnet unreachable | Route approval missing — open Headplane → Machines → approve the advertised subnet route |
| `iptables` blocks container traffic | Confirm `/etc/docker/daemon.json` has `"iptables": false` and that `docker info` shows the change |

Other pointers:

- Container logs: `docker logs headscale`, `docker logs headplane`
- Headscale health: `curl http://127.0.0.1:9090/metrics` (or via SSH tunnel)
- Routes on peers: `ip route | grep $LAB_SUBNET`

## Quick command summary

```bash
# Start services
cd headscale/ && docker compose up -d

# Headplane login (no OIDC)
docker exec headscale headscale apikeys create --expiration 999d

# Create user and pre-auth key
docker exec headscale headscale users create <user>
docker exec headscale headscale preauthkeys create -u <user> -e 24h

# Lab host: subnet router
TS_ALLOW_INSECURE=1 tailscale up --login-server http://$HEADSCALE_HOST:8080 \
  --accept-routes --advertise-routes=$LAB_SUBNET

# Approve interactive registration
docker exec headscale headscale nodes register --user <user> --key <REGISTRATION_TOKEN>

# Peers (accept routes)
TS_ALLOW_INSECURE=1 tailscale up --login-server http://$HEADSCALE_HOST:8080 --accept-routes
```

## See also

- **[Headscale quick start](30-headscale-quick-setup.md)** — the five-command happy path.
- **[Network access](25-network-enclosure.md)** — the family of alternative boundary options.
- **[Security model](../30-server/30-security.md)** — what the tailnet is and isn't protecting against.
- **[Operator runbook](../30-server/10-administration.md)** — install the lab service itself behind the tailnet.
- **[Headscale upstream](https://headscale.net/)** — authoritative reference for the control plane.
- **[Tailscale subnet router docs](https://tailscale.com/kb/1019/subnets)** — what `--advertise-routes` actually does on the wire.
