---
title: Headscale VPN — Quick setup
description: Stand up Headscale + Headplane on the lab host with Docker Compose, register the host as a subnet router, connect one peer — the happy path in five commands.
tags: [how-to, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Headscale VPN — Quick setup

*Five-command happy path — Headscale + Headplane via Docker Compose, the lab host as a subnet router, one client peer reaching the lab subnet.*

The lab service ships [without HTTP authentication](../30-server/30-security.md), so deployment lives or dies on the network boundary. This page is the five-command happy path: a [Headscale](https://headscale.net/) control plane, the [Headplane](https://github.com/tale/headplane) UI, the lab host as a subnet router, and one client peer that can reach the lab subnet. For ACLs, OIDC, and troubleshooting tables, see [Headscale VPN — Reference](30-headscale-reference.md).

!!! info "Placeholder convention"
    Substitute `$HEADSCALE_HOST` with your Headscale server's IP or DNS name (`export HEADSCALE_HOST=lab.example.com`) and `$LAB_SUBNET` with the IPv4 CIDR of the lab network (`export LAB_SUBNET=192.168.121.0/24`). The libvirt default is `192.168.121.0/24`; a Containerlab-only host typically uses a `172.20.20.0/24` management bridge.

!!! warning "Replace the `CHANGE-ME.example` placeholder"
    `headscale/config/config.yaml` and `headscale/headplane.config.yaml` ship with `CHANGE-ME.example` placeholders. Headscale will refuse to start, and Tailscale clients cannot register, until you replace both with a host every peer can reach (`http://$HEADSCALE_HOST:8080`, or an `https://headscale.example.com` URL behind a reverse proxy with TLS).

## Prerequisites

- **Docker and Docker Compose.**
- **Network egress** to reach client devices.
- A clone of this repository. The Compose file and config templates live under `headscale/`.

## What you'll deploy

<!-- trace: headscale/docker-compose.yml:32-33 -->

- A Headscale server listening on `:8080` (HTTP API) and `:9090` (metrics)
- A Headplane UI on `:3000`
- Bind-mounted state directories under `headscale/lib/`, `headscale/run/`, and `headscale/headplane-data/` (auto-created on first `docker compose up`)

The services can run on the Remote Lab VM or on any reachable host — clients only need to reach `server_url`.

## Start the services

```bash
cd headscale/
docker compose up -d
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
```

Expected ports on the host: `8080` (Headscale API), `9090` (Headscale metrics), `3000` (Headplane UI).

Open the Headplane UI at `http://$HEADSCALE_HOST:3000/admin`. If the VM's IP isn't directly reachable, SSH-tunnel:

```bash
ssh -L 3000:localhost:3000 root@$HEADSCALE_HOST
# Then open http://127.0.0.1:3000/admin
```

!!! warning "HTTP-only login requires `cookie_secure=false`"
    The shipped config sets `server.cookie_secure=false` so login works without HTTPS. Flip back to `true` once HTTPS sits in front (see Reference).

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

`TS_ALLOW_INSECURE=1` lets the Tailscale client talk to a plain-HTTP control plane and skip cert validation. Acceptable for internal-trust testing on a local tailnet; drop it once HTTPS is in front.

Approve the route advertisement in Headplane → Machines → select the new node → enable advertised routes.

## System settings on the lab host

```bash
# Disable Docker iptables interference when bridging to lab networks
sudo mkdir -p /etc/docker
echo '{"iptables": false}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker

# Enable IPv4 forwarding (idempotent sysctl.d drop-in)
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-forwarding.conf
sudo sysctl --system
```

A drop-in under `/etc/sysctl.d/` is idempotent and sidesteps the GNU-vs-BSD `sed -i` dialect split.

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

- **[Headscale VPN — Reference](30-headscale-reference.md)** — ACLs, user management, system settings, troubleshooting.
- **[Administration](../30-server/10-administration.md)** — install the lab service itself behind the tailnet you just stood up.
- **[Security model](../30-server/30-security.md)** — what the tailnet is protecting against, and what it isn't.
