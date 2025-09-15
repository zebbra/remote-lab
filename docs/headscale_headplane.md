## Headscale + Headplane with Docker Compose (for Remote Lab networking)

This guide shows how to deploy a self‑hosted [Headscale](https://headscale.net/) control plane (compatible with Tailscale clients) with a [Headplane](https://github.com/tale/headplane) web UI using Docker Compose, and how to connect your Remote Lab VM and peers. For client behavior and concepts, see the [Tailscale docs](https://tailscale.com/kb/). If you need low‑level server details, see the [Headscale repo](https://github.com/juanfont/headscale).

---

### What you will deploy

- A Headscale server listening on `:8080` (HTTP API) and `:9090` (metrics)
- A Headplane UI on `:3000`, configured to talk to Headscale
- Persistent volumes for Headscale state and Headplane data

The Compose files and configuration in this repo are located at:

```
neops_worker_sdk/testing/remote_lab/headscale/
  ├─ docker-compose.yml
  ├─ headplane.config.yaml
  └─ config/
     ├─ config.yaml
     └─ derp.yaml
```

> **Important**: The services can run on the Remote Lab VM or on any reachable host. They do not have to run on the same VM as the Remote Lab server.

---

## 1) Prerequisites

- Docker and Docker Compose installed
- Network egress to reach client devices (Remote Lab subnet and peers)
- Optional but recommended: reverse proxy or SSH access for port forwarding (see Access section)

---

## 2) Configure Headscale and Headplane (already provided)

This repository includes working templates:


### `config/config.yaml` — Headscale configuration
`server_url` is set to `http://127.0.0.1:8080` by default. If clients will reach your server at a public IP or DNS name, update this value accordingly (e.g., `http://91.99.184.46:8080`).
  
**Critical**: In our example `http://91.99.184.46` is the URL that clients are told to use for control‑plane calls. It must be reachable from every client. 

DNS/MagicDNS and DERP settings are present and can be adjusted later.

### `headplane.config.yaml` — Headplane configuration
  - Points to Headscale at `http://headscale:8080` (the Compose service name) and mounts Headscale’s `config.yaml` as read‑only for visibility in the UI.

### `docker-compose.yml` — brings up both containers and mounts volumes:
- `headscale`: exposes `8080` and `9090`, persists `/var/lib/headscale`, mounts `./config` at `/etc/headscale`.

- `headplane`: exposes `3000`, persists `/var/lib/headplane`, mounts the Headscale config for UI introspection.

You typically do not need to edit these files to get started beyond optionally changing `server_url` in `config/config.yaml` and even

---

## 3) Start Headscale and Headplane

From the repository root, change into the Headscale directory and start services:

```bash
cd neops_worker_sdk/testing/remote_lab/headscale
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

###
You should be able to reach all your services via: `http://<VM_PUBLIC_IP>:<SERVICE_PORT>`.

To open the Headplane UI on our neops-labs VM you should be able to use: 
http://91.99.184.46:3000/admin

> **Important**: When you are running Headscale/Headplane without HTTPS this only works when `server.cookie_secure` in the Headplane config is set to `false`.

### SSH port forwarding
If for some reason the services are not reachable through the VMs IP, you can use SSH port forwarding to reach it via `localhost`.

```bash
ssh -L 3000:localhost:3000 root@<server_ip>
```

Then you can open Headplane at http://127.0.0.1:3000/admin

### Reverse proxy + HTTPS + DNS (recommended, to be added)

Use a proper reverse proxy (e.g., Nginx/Caddy/Traefik) with HTTPS and a DNS name so `server_url` is a stable, secure URL like `https://headscale.example.com`. This is the recommended production setup and will probably be added here later on.

---

## 5) Authenticate Headplane (no OIDC)

If you do not configure OIDC, generate a Headscale API key and use it to sign into Headplane:

```bash
docker exec headscale headscale apikeys create --expiration 999d
```

Copy the key and open `Headplane` via http://91.99.184.46:3000/admin or via `localhost` with **SSH Port forwarding** . Sign in using the API key.

> You can add OIDC later; see examples in `headplane.config.yaml` and Headplane docs.

---

## 6) Manage users and auth keys

You can manage users and pre‑auth keys via the Headscale CLI or Headplane UI.

### Headplane UI (preferred to start)

Open the UI, add users, and generate/inspect pre‑auth keys from the Users and Keys sections. If OIDC is configured, user management may be backed by your identity provider.

### Headscale CLI (concise equivalent)

```bash
# Create a user (owning machines and pre‑auth keys)
docker exec headscale headscale users create <user>

# Create a pre‑auth key for that user (valid 24h)
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


#### Why `TS_ALLOW_INSECURE=1` ?

*What it does:* allows the Tailscale client to talk to a Headscale `--login-server` over plain HTTP (no TLS) and to skip certificate validation.


### 7.1 Remote Lab host (subnet router)

On the Remote Lab VM, install Tailscale and advertise the lab subnet. Example for the `192.168.121.0/24` lab:

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://91.99.184.46:8080 \
  --accept-routes \
  --reset \
  --advertise-routes=192.168.121.0/24
```

This prints an authentication URL such as:

```
To authenticate, visit:

    http://91.99.184.46:8080/register/8otva4j_QEUEmG1ZNjlShdgC

Success.
```

Approve the node using one of the following methods:


#### Headplane UI:
Open Headplane → Machines → locate the pending registration → approve using the token `8otva4j_QEUEmG1ZNjlShdgC`.

#### Headscale CLI (from the host running Headscale):

  ```bash
  docker exec headscale headscale nodes register --user <user> --key 8otva4j_QEUEmG1ZNjlShdgC
  ```


> After approval, the Remote Lab host will appear in your tailnet. In Headplane, you can enable/approve the advertised subnet routes if required. See the TS_ALLOW_INSECURE note above for when plain HTTP is acceptable during testing.

### 7.2 Peer devices

Run on each peer that needs access to the lab network:

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://91.99.184.46:8080 \
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
sudo systemctl restart docker || true

# Enable IPv4 forwarding
sudo sysctl -w net.ipv4.ip_forward=1
sudo sed -i '' 's/^#\?net.ipv4.ip_forward.*/net.ipv4.ip_forward = 1/' /etc/sysctl.conf
sudo sysctl -p || true
```

---

## 9) Notes, tips, and next steps

- **Where to run**: Headscale/Headplane can run on the Remote Lab VM or elsewhere; only requirement is that clients can reach `server_url`.
- **TLS**: If you enable TLS or use a reverse proxy with HTTPS, update `server_url` to `https://…` and configure certs accordingly.
- **DERP**: For constrained NATs, consider enabling embedded DERP (requires TLS) or referencing external DERP maps; see comments in `config/config.yaml`.
- **Pre‑auth keys**: Instead of interactive approval, you may create reusable or ephemeral pre‑auth keys via the Headscale CLI and pass them to clients with `tailscale up --auth-key=<key>`.

Troubleshooting pointers:
- Check container logs: `docker logs headscale`, `docker logs headplane`
- Verify Headscale health: open `http://127.0.0.1:9090/metrics` (or via SSH tunnel)
- Confirm routes on peers: `ip route | grep 192.168.121.0/24`

---

## Quick command summary

Bold headings, single commands – easy to scan and copy.

**Start services**
```bash
cd neops_worker_sdk/testing/remote_lab/headscale
docker compose up -d
```

**Headplane login (no OIDC)**
```bash
docker exec headscale headscale apikeys create --expiration 999d
```

**Create user and pre‑auth key**
```bash
docker exec headscale headscale users create <user>
docker exec headscale headscale preauthkeys create -u <user> -e 24h
```

**Remote Lab VM (subnet router)**
```bash
TS_ALLOW_INSECURE=1 tailscale up --login-server http://91.99.184.46:8080 --accept-routes --advertise-routes=192.168.121.0/24
```

**Approve interactive registration (example token)**
```bash
docker exec headscale headscale nodes register --user <user> --key 8otva4j_QEUEmG1ZNjlShdgC
```

**Peers (accept routes)**
```bash
TS_ALLOW_INSECURE=1 tailscale up --login-server http://91.99.184.46:8080 --accept-routes
```



