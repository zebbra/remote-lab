---
title: Headscale Quick start
description: Stand up Headscale + Headplane on the lab host with Docker Compose, register the host as a subnet router, connect one peer — the happy path in five commands.
tags: [how-to, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Headscale quick start

*Five-command happy path — Headscale + Headplane via Docker Compose, the lab host as a subnet router, one client peer reaching the lab subnet.*

[Headscale](https://headscale.net/) is an open-source, [Tailscale](https://tailscale.com/)-compatible VPN control plane; [Headplane](https://github.com/tale/headplane) is the matching web UI. **The reference Remote Lab deployment uses both** — free to run, fully auditable, no per-seat cost — which is why this repo ships Compose templates for them. **Substitute your own VPN any time:** the lab service is unaware of which boundary surrounds it, and the host-side prerequisites on this page apply equally. The [Network access](25-network-enclosure.md) page lists the alternatives (managed Tailscale, NetBird, ZeroTier, plain WireGuard, network-layer ACLs, application-layer mTLS).

This page produces a Headscale control plane on `:8080`, the Headplane UI on `:3000`, the lab host registered as a subnet router, and one client peer reaching the lab subnet. For ACLs, OIDC, and troubleshooting tables, see [Headscale reference](40-headscale-reference.md).

## Prerequisites

- **A clone of this repository.** The Compose file and config templates live under `headscale/` — every step below assumes you're on the host that will run these services with the repo checked out.
- **Docker and Docker Compose.**
- **Network egress** to reach client peers.

## What you'll deploy

<!-- trace: headscale/docker-compose.yml:32-33 -->

- A Headscale server listening on `:8080` (HTTP API) and `:9090` (metrics)
- A Headplane UI on `:3000`
- Bind-mounted state directories under `headscale/lib/`, `headscale/run/`, and `headscale/headplane-data/` (auto-created on first `docker compose up`)

The services can run on the Remote Lab VM or on any reachable host — clients only need to reach `server_url`.

## Configure

!!! info "Placeholder convention"
    Throughout the rest of this page, substitute `$HEADSCALE_HOST` with your Headscale server's IP or DNS name (`export HEADSCALE_HOST=lab.example.com`) and `$LAB_SUBNET` with the IPv4 CIDR of the lab network (`export LAB_SUBNET=192.168.121.0/24`). The libvirt default is `192.168.121.0/24`; a Containerlab-only host typically uses a `172.20.20.0/24` management bridge.

Three placeholders ship in the repo and must be replaced before `docker compose up` will succeed. Both fixes are one-shot sed commands; run them once per clone, then move on to **Start the services**.

### Set `server_url` and `public_url` to a reachable host

`headscale/config/config.yaml` and `headscale/headplane.config.yaml` ship with `CHANGE-ME.example` placeholders. Headscale refuses to start, and Tailscale clients cannot register, until both are replaced with a host every peer can reach. With `$HEADSCALE_HOST` exported:

```bash
sed -i.bak "s|CHANGE-ME.example|$HEADSCALE_HOST|g" \
  headscale/config/config.yaml \
  headscale/headplane.config.yaml \
  && rm headscale/config/config.yaml.bak headscale/headplane.config.yaml.bak
```

For production, replace with an `https://headscale.example.com` URL behind a reverse proxy with TLS — see [Reference → Reverse proxy + HTTPS + DNS](40-headscale-reference.md#reverse-proxy-https-dns).

### Generate the Headplane cookie secret

`headscale/headplane.config.yaml` ships with `cookie_secret: "CHANGE_ME_GENERATE_RANDOM_SECRET"`. Headplane uses this to sign browser sessions and refuses to start until it's replaced with a real 32-character value:

```bash
sed -i.bak "s/CHANGE_ME_GENERATE_RANDOM_SECRET/$(openssl rand -hex 16)/" \
  headscale/headplane.config.yaml \
  && rm headscale/headplane.config.yaml.bak
```

Run **once per clone**. The command is idempotent — re-running after the placeholder is gone is a no-op (sed finds no match).

### Verify

```bash
grep -E "(server_url|public_url|cookie_secret)" \
  headscale/config/config.yaml \
  headscale/headplane.config.yaml
```

You should see your `$HEADSCALE_HOST` value and a random hex string, not the original placeholders.

!!! danger "**Cookie secret: NOT suitable for shared deployments without changes**"
    The bootstrap above writes a random `cookie_secret` directly into `headplane.config.yaml`. That's fine on a single-operator host. For **anything shared** (multiple operators, a team-owned host, CI runners with any access to the box), store the secret outside the repo before going live: drop it in a sealed-secret store (Vault, SOPS-encrypted file, your CI's secrets store) and template it in at deploy time. **Anyone who reads the secret — from Git history, a backup, a leaked file — can forge admin sessions for your tailnet**, including ACL changes and machine deletion.

## Prepare the lab host {#prepare-the-lab-host}

Two host-level settings must be in place before peers can reach the lab subnet through the tunnel. Both are idempotent — re-running is safe.

```bash
# 1. Disable Docker iptables interference when bridging to lab networks
sudo mkdir -p /etc/docker
echo '{"iptables": false}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker

# 2. Enable IPv4 forwarding (sysctl.d drop-in survives reboots)
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-forwarding.conf
sudo sysctl --system
```

**Neither setting is Headscale-specific.** Docker `iptables: false` is a Containerlab concern and applies regardless of which boundary you choose. IPv4 forwarding is required whenever the host bridges peers into the lab subnet — i.e. for any subnet-router setup (Tailscale, NetBird, ZeroTier, plain WireGuard, internal VLAN). The exception is family 5 (application-layer proxy) which doesn't need forwarding. See [Network access → Host settings that carry over](25-network-enclosure.md#host-settings) for the per-family table.

## Start the services

```bash
cd headscale/
docker compose up -d
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
```

Expected ports on the host: `8080` (Headscale API), `9090` (Headscale metrics), `3000` (Headplane UI).

Open the Headplane UI at `http://$HEADSCALE_HOST:3000/admin`. If the host's IP isn't directly reachable from your laptop (private network, no DNS), forward `:3000` over SSH instead:

```bash
ssh -L 3000:localhost:3000 <user>@$HEADSCALE_HOST
# Then on your laptop, open http://127.0.0.1:3000/admin
```

For what this does and the two other access patterns (tailnet IP after the lab host is registered, reverse proxy with HTTPS for production), see [Reference → Reaching the UI](40-headscale-reference.md#reaching-the-ui).

!!! warning "Headplane has no authentication on the shipped config"
    The shipped config has no OIDC and no built-in auth — the only barrier is reaching `:3000`. **In any shared deployment, the Headplane UI must not be exposed to anyone who shouldn't have full tailnet admin access.** Two layers of defense:
    
    -   **Don't bind `:3000` to a public interface.** Reach it via the SSH tunnel above, or behind an SSO-aware reverse proxy.
    -   **For shared deployments: configure OIDC** (see [Reference → OIDC](40-headscale-reference.md#oidc-optional)) before any non-operator gets tailnet access.
    
    The shipped config also sets `server.cookie_secure=false` so login works over plain HTTP. Flip it back to `true` and put HTTPS in front before going live ([Reference → Reverse proxy](40-headscale-reference.md#reverse-proxy-https-dns)).

## Authenticate Headplane (no OIDC)

Generate a Headscale API key and use it to sign into Headplane:

```bash
docker exec headscale headscale apikeys create --expiration 999d
```

Copy the key, sign in. (For OIDC, add later — see Reference.)

## Create a user and a pre-auth key

```bash
docker exec headscale headscale users create lab-host
docker exec headscale headscale preauthkeys create -u lab-host -e 24h
```

Capture the printed key — you'll pass it to `tailscale up` next.

## Register the lab host as a subnet router

On the **Remote Lab VM**, install Tailscale and join the tailnet, advertising the lab subnet:

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://$HEADSCALE_HOST:8080 \
  --auth-key <PRE_AUTH_KEY> \
  --accept-routes \
  --reset \
  --advertise-routes=$LAB_SUBNET
```

!!! warning "**`TS_ALLOW_INSECURE=1` — single-operator labs only**"
    This flag tells the Tailscale client to talk to a plain-HTTP control plane and skip certificate validation. **It opens a person-in-the-middle window** for every peer registration on this tunnel. Acceptable for a single-operator lab on a host you control end-to-end. **Not acceptable when more than one peer (CI runner, teammate's laptop) shares the tunnel** — drop it once HTTPS is in front of Headscale ([Reference → Reverse proxy](40-headscale-reference.md#reverse-proxy-https-dns)).

Approve the route advertisement in Headplane → Machines → select the new node → enable advertised routes.

## Connect a peer

On the laptop or CI runner that needs to reach the lab subnet:

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://$HEADSCALE_HOST:8080 \
  --accept-routes \
  --reset
```

Approve in Headplane. Once routes are approved, the peer can reach the lab subnet directly.

Confirm:

```bash
ip route | grep $LAB_SUBNET
curl -fsS "http://<lab-host-tailnet-ip>:8000/healthz" && echo OK
```

## What to do next

- **[Headscale reference](40-headscale-reference.md)** — ACLs, user management, system settings, troubleshooting (Headscale-specific).
- **[Network access](25-network-enclosure.md)** — the family of alternatives if you want to compare Headscale to managed mesh VPN services, plain WireGuard, network-layer ACLs, or application-layer mTLS. The system settings on this page (Docker `iptables: false`, IPv4 forwarding) carry over regardless of which option you pick.
- **[Security model](../30-server/30-security.md)** — what the network boundary is protecting against, and what it isn't.

Next: **[Run the service →](../30-server/index.md)** — install `neops-remote-lab` itself behind the boundary you just stood up.
