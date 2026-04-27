---
title: Headscale VPN
description: Deploy a self-hosted Headscale control plane plus the Headplane UI with Docker Compose to give remote lab clients private subnet reachability.
tags: [how-to, deployment, operator]
crosslink_defines: []
crosslink_references: []
---

# Headscale + Headplane with Docker Compose

*Private subnet reachability into Netlab topologies without exposing the host.*

Clients need to reach Netlab lab subnets that live inside a host's libvirt network. A small [Headscale](https://headscale.net/) control plane (a self-hosted, Tailscale-compatible coordination server) plus [Headplane](https://github.com/tale/headplane) (a web UI for Headscale) and [Tailscale](https://tailscale.com/kb/) peers give you that reachability without exposing the host. For low-level server details, see the upstream [Headscale repo](https://github.com/juanfont/headscale).

!!! note "Placeholder convention"
    Throughout this guide, substitute `$HEADSCALE_HOST` with your Headscale server's IP or DNS name (`export HEADSCALE_HOST=lab.example.com`) and `$LAB_SUBNET` with the IPv4 CIDR of the lab network you want to advertise (`export LAB_SUBNET=192.168.121.0/24`). The `192.168.121.0/24` value used in the `tailscale up` examples is the libvirt default; a Containerlab-only host typically uses a `172.20.20.0/24` management bridge — set `LAB_SUBNET` to whatever your provider allocates. Examples use environment-variable form so commands are copy-pasteable once you export the variables.

!!! warning "The shipped configs need a real `server_url` before they will work"
    `headscale/config/config.yaml` and `headscale/headplane.config.yaml` ship with `CHANGE-ME.example` placeholders — Headscale will refuse to start, and Tailscale clients cannot register, until you replace both with a host every peer can reach. Set them to your `$HEADSCALE_HOST` (or, for production, an `https://headscale.example.com` URL behind a reverse proxy with TLS).

---

## What you will deploy

<!-- trace: headscale/docker-compose.yml:32-33 -->
- A Headscale server listening on `:8080` (HTTP API) and `:9090` (metrics)
- A Headplane UI on `:3000`, configured to talk to Headscale
- Bind-mounted state directories under `headscale/lib/`, `headscale/run/`, and `headscale/headplane-data/` (auto-created on first `docker compose up`)

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

!!! info
    The services can run on the Remote Lab VM or on any reachable host. They do not have to run on the same VM as the Remote Lab server.

---

## 1) Prerequisites

- Docker and Docker Compose installed
- Network egress to reach client devices (Remote Lab subnet and peers)
- Optional but recommended: reverse proxy or SSH access for port forwarding (see Access section)

---

## 2) Configure Headscale and Headplane (already provided)

This repository includes working templates:

### `config/config.yaml` — Headscale configuration

<!-- trace: headscale/config/config.yaml:13 -->
The shipped value of `server_url` is the placeholder `http://CHANGE-ME.example:8080`. You MUST override this to a host or IP your clients can reach — for production, a `https://headscale.example.com` URL behind a reverse proxy with TLS is the recommended shape. For local testing, `http://127.0.0.1:8080` works if every client is on the same host.

!!! warning "Clients must reach `server_url`"
    Whatever you set `server_url` to, it must be reachable from every Tailscale peer that will join the tailnet. A peer that cannot reach the control plane cannot register.

DNS/MagicDNS and DERP settings are present and can be adjusted later.

### `headplane.config.yaml` — Headplane configuration

<!-- trace: headscale/headplane.config.yaml:23 -->
Points to Headscale at `http://headscale:8080` (the Compose service name) and mounts Headscale's `config.yaml` for visibility in the UI.

### `docker-compose.yml` — brings up both containers and bind-mounts state:

<!-- trace: headscale/docker-compose.yml:35 -->
- `headscale`: exposes `8080` and `9090`, bind-mounts `./lib` at `/var/lib/headscale`, `./run` at `/var/run/headscale`, and `./config` at `/etc/headscale`.
- `headplane`: exposes `3000`, bind-mounts `./headplane-data` at `/var/lib/headplane`, mounts the Headscale config for UI introspection.

For a first run you typically only need to change `server_url` in `config/config.yaml` (see above) and, if you want Headscale to serve extra DNS records, populate `config/dns_records.json`.

---

## 3) Start Headscale and Headplane

From the repository root, change into the Headscale directory and start services:

```bash
cd headscale/
docker compose up -d

# Verify containers
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
```

Expected ports (host):

- Headscale API: `8080`
- Headscale metrics: `9090`
- Headplane UI: `3000`

---

## 4) Accessing the services

### Direct access via VM public IP

You should be able to reach all your services via: `http://$HEADSCALE_HOST:<SERVICE_PORT>`.

To open the Headplane UI, point your browser at `http://$HEADSCALE_HOST:3000/admin`.

!!! warning "HTTP-only login requires `cookie_secure=false`"
    When you are running Headscale/Headplane without HTTPS, login only works when `server.cookie_secure` in the Headplane config is set to `false`. The shipped config already sets this (see `headscale/headplane.config.yaml:13`); flip it back to `true` once you put HTTPS in front.

### SSH port forwarding

If for some reason the services are not reachable through the VM's IP, you can use SSH port forwarding to reach it via `localhost`.

```bash
ssh -L 3000:localhost:3000 root@$HEADSCALE_HOST
```

Then you can open Headplane at `http://127.0.0.1:3000/admin`.

### Reverse proxy + HTTPS + DNS (recommended, to be added)

Use a proper reverse proxy (e.g., Nginx/Caddy/Traefik) with HTTPS and a DNS name so `server_url` is a stable, secure URL like `https://headscale.example.com`. This is the recommended production setup and will probably be added here later on.

---

## 5) Authenticate Headplane (no OIDC)

If you do not configure OIDC, generate a Headscale API key and use it to sign into Headplane:

```bash
docker exec headscale headscale apikeys create --expiration 999d
```

Copy the key and open Headplane via `http://$HEADSCALE_HOST:3000/admin` (or via `localhost` with **SSH port forwarding**). Sign in using the API key.

!!! info
    You can add OIDC later; see examples in `headplane.config.yaml` and Headplane docs.

---

## 6) Manage users and auth keys

You can manage users and pre-auth keys via the Headscale CLI or Headplane UI.

### Headplane UI (preferred to start)

Open the UI, add users, and generate/inspect pre-auth keys from the Users and Keys sections. If OIDC is configured, user management may be backed by your identity provider.

### Headscale CLI (concise equivalent)

```bash
# Create a user (owning machines and pre-auth keys)
docker exec headscale headscale users create <user>

# Create a pre-auth key for that user (valid 24h)
docker exec headscale headscale preauthkeys create -u <user> -e 24h

# Optional flags:
#   --ephemeral   create an ephemeral key (machine disappears when inactive)
#   -r            reusable key (can be used multiple times)
```

You can use such a key with the Tailscale client: `tailscale up --login-server <url> --auth-key <key>` to skip interactive approval.

---

## 7) Connect clients (Tailscale)

You will connect two types of clients:

- The **Remote Lab host** (acts as a subnet router to your lab network)
- Other **peer devices** (laptops/CI/servers) that need to reach the lab network

### 7.1 Remote Lab host (subnet router)

On the Remote Lab VM, install Tailscale and advertise the lab subnet:

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://$HEADSCALE_HOST:8080 \
  --accept-routes \
  --reset \
  --advertise-routes=$LAB_SUBNET
```

!!! info "Why `TS_ALLOW_INSECURE=1`?"
    Allows the Tailscale client to talk to a Headscale `--login-server` over plain HTTP (no TLS) and to skip certificate validation. Acceptable for internal-trust testing on a local tailnet; drop it as soon as the control plane is behind HTTPS.

This prints an authentication URL such as:

```
To authenticate, visit:

    http://$HEADSCALE_HOST:8080/register/<REGISTRATION_TOKEN>

Success.
```

Approve the node using one of the following methods:

#### Headplane UI

Open Headplane → Machines → locate the pending registration → approve using the registration token from the CLI output (example token: `8otva4j_QEUEmG1ZNjlShdgC` — yours will differ).

#### Headscale CLI (from the host running Headscale)

```bash
docker exec headscale headscale nodes register --user <user> --key <REGISTRATION_TOKEN>
```

!!! info
    After approval, the Remote Lab host will appear in your tailnet. In Headplane, you can enable/approve the advertised subnet routes if required. See the `TS_ALLOW_INSECURE` note above for when plain HTTP is acceptable during testing.

### 7.2 Peer devices

Run on each peer that needs access to the lab network:

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://$HEADSCALE_HOST:8080 \
  --accept-routes \
  --reset
```

Approve each device with the same process as above (Headplane or CLI). Once approved, peers learn the lab subnet route from the Remote Lab host (after you approve routes).

---

## 8) Remote Lab host: system settings

Ensure the Remote Lab VM is prepared for subnet routing:

```bash
# Disable Docker iptables interference when bridging to lab networks
sudo mkdir -p /etc/docker
echo '{"iptables": false}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker

# Enable IPv4 forwarding (sysctl.d drop-in — idempotent, no sed dialect dependency)
echo 'net.ipv4.ip_forward=1' | sudo tee /etc/sysctl.d/99-forwarding.conf
sudo sysctl --system
```

> **Why `sysctl.d` over `sed -i`?**
> A drop-in file under `/etc/sysctl.d/` is idempotent, survives a re-run without double-writing, and sidesteps the GNU-vs-BSD `sed -i` dialect split (BSD requires `sed -i ''`; GNU rejects it). Re-running the block reloads cleanly via `sysctl --system`.

---

## 9) Notes, tips, and next steps

- **Where to run**: Headscale/Headplane can run on the Remote Lab VM or elsewhere; only requirement is that clients can reach `server_url`.
- **TLS**: If you enable TLS or use a reverse proxy with HTTPS, update `server_url` to `https://…` and configure certs accordingly.
- **DERP**: For constrained NATs, consider enabling embedded DERP (requires TLS) or referencing external DERP maps; see comments in `config/config.yaml`.
- **Pre-auth keys**: Instead of interactive approval, you may create reusable or ephemeral pre-auth keys via the Headscale CLI and pass them to clients with `tailscale up --auth-key=<key>`.

### Troubleshooting

| Symptom | Check |
|---|---|
| `docker compose up` fails with port in use | `sudo ss -ltnp \| grep -E ':(3000\|8080\|9090)'` — another service owns the port |
| Headplane login spins / 401 loop over HTTP | `server.cookie_secure` in `headplane.config.yaml` is `true`; flip to `false` for plain-HTTP access |
| Tailscale client "cannot reach control-plane" | `$HEADSCALE_HOST` not reachable from the client; use SSH port-forwarding or fix DNS/firewall |
| Peers approved but lab subnet unreachable | Route approval missing — open Headplane → Machines → approve the advertised subnet route |
| `iptables` blocks container traffic | Confirm `/etc/docker/daemon.json` has `"iptables": false` and that `docker info` shows the change |

Other pointers:

- Check container logs: `docker logs headscale`, `docker logs headplane`
- Verify Headscale health: `curl http://127.0.0.1:9090/metrics` (or via SSH tunnel)
- Confirm routes on peers: `ip route | grep $LAB_SUBNET`

---

## Quick command summary

**Start services**

```bash
cd headscale/
docker compose up -d
```

**Headplane login (no OIDC)**

```bash
docker exec headscale headscale apikeys create --expiration 999d
```

**Create user and pre-auth key**

```bash
docker exec headscale headscale users create <user>
docker exec headscale headscale preauthkeys create -u <user> -e 24h
```

**Remote Lab VM (subnet router)**

```bash
TS_ALLOW_INSECURE=1 tailscale up --login-server http://$HEADSCALE_HOST:8080 --accept-routes --advertise-routes=$LAB_SUBNET
```

**Approve interactive registration (example token)**

```bash
docker exec headscale headscale nodes register --user <user> --key <REGISTRATION_TOKEN>
```

**Peers (accept routes)**

```bash
TS_ALLOW_INSECURE=1 tailscale up --login-server http://$HEADSCALE_HOST:8080 --accept-routes
```
