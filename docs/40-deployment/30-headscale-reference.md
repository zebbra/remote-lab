---
title: Headscale VPN — Reference
description: ACL configuration, user and pre-auth key management, system settings, troubleshooting, and the full command summary for a deployed Headscale tailnet.
tags: [reference, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Headscale VPN — Reference

For the five-command happy path, see [Headscale VPN — Quick setup](20-headscale-quick-setup.md). This page covers the configuration surface you reach for once the tailnet is running — ACLs, user management, the Compose+config layout, troubleshooting, and a quick command summary.

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
Points to Headscale at `http://headscale:8080` (the Compose service name) and mounts Headscale's `config.yaml` for visibility in the UI.

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

Manage users and pre-auth keys via the Headscale CLI or the Headplane UI.

### Headplane UI

Open the UI, add users, and generate/inspect pre-auth keys from the Users and Keys sections. If OIDC is configured, user management is backed by your identity provider.

### Headscale CLI

```bash
# Create a user (owns machines and pre-auth keys)
docker exec headscale headscale users create <user>

# Create a pre-auth key for that user (valid 24h)
docker exec headscale headscale preauthkeys create -u <user> -e 24h

# Optional flags:
#   --ephemeral   create an ephemeral key (machine disappears when inactive)
#   -r            reusable key (can be used multiple times)
```

Use such a key with `tailscale up --auth-key <key>` to skip interactive approval.

## ACL configuration

Headscale supports ACLs (access-control lists) that restrict which tailnet members can reach which destinations. Configure ACLs in `config/config.yaml` under `acl_policy_path`, pointing at a HuJSON policy file. Reload with:

```bash
docker exec headscale headscale policy check
docker compose restart headscale
```

For the policy file format, see [Headscale ACL docs](https://headscale.net/stable/ref/acls/). At minimum, restrict access to the lab subnet to the users and tags that need it; "default-allow" leaves the lab service exposed to every peer on the tailnet.

## OIDC (optional)

You can add OIDC for user management; see examples in `headplane.config.yaml` and the upstream [Headplane docs](https://github.com/tale/headplane). Set `server.cookie_secure = true` once you sit HTTPS in front.

## System settings

Three settings on the lab host that the [Quick setup](20-headscale-quick-setup.md#system-settings-on-the-lab-host) page applies:

| Setting | Why |
|---|---|
| `iptables: false` in `/etc/docker/daemon.json` | Stops Docker's iptables rules from blocking container traffic across the bridged lab network. |
| `net.ipv4.ip_forward=1` (sysctl.d drop-in) | Required for the lab host to act as a subnet router. |
| Tailscale `--accept-routes` on peers | Without this, peers ignore advertised subnet routes from the lab host. |

Use a sysctl.d drop-in over `sed -i` — idempotent, survives a re-run without double-writing, and sidesteps the GNU-vs-BSD `sed -i` dialect split.

## DERP

For constrained NATs, consider enabling embedded DERP (requires TLS) or referencing external DERP maps; see comments in `config/config.yaml`.

## Troubleshooting

| Symptom | Check |
|---|---|
| `docker compose up` fails with port in use | `sudo ss -ltnp \| grep -E ':(3000\|8080\|9090)'` — another service owns the port |
| Headplane login spins / 401 loop over HTTP | `server.cookie_secure` in `headplane.config.yaml` is `true`; flip to `false` for plain-HTTP access |
| Tailscale client "cannot reach control-plane" | `$HEADSCALE_HOST` not reachable from the client; use SSH port-forwarding or fix DNS/firewall |
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

- **[Headscale VPN — Quick setup](20-headscale-quick-setup.md)** — the five-command happy path.
- **[Security model](../30-server/30-security.md)** — what the tailnet is and isn't protecting against.
- **[Administration](../30-server/10-administration.md)** — install the lab service itself behind the tailnet.
- **[Headscale upstream](https://headscale.net/)** — authoritative reference for the control plane.
- **[Tailscale subnet router docs](https://tailscale.com/kb/1019/subnets)** — what `--advertise-routes` actually does on the wire.
