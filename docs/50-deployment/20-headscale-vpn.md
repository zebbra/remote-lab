---
page_purpose: how-to
personas_served:
  - devops-engineer
  - senior-network-architect
difficulty_level: intermediate
---

# Headscale VPN

This page deploys a self-hosted [Headscale](https://headscale.net/) control plane (a Tailscale-compatible coordination server) plus a [Headplane](https://github.com/tale/headplane) web UI with Docker Compose, then connects the Remote Lab VM and peer machines (laptops, CI runners) to the resulting tailnet. The result is a VPN that lets test runners reach lab container subnets without exposing the lab host to the public internet. For client behavior and concepts, see the [Tailscale docs](https://tailscale.com/kb/); for low-level server details, see the [Headscale repo](https://github.com/juanfont/headscale).

## Placeholders used on this page

Throughout this page, `<HEADSCALE_HOST>` refers to your Headscale server's reachable IP or DNS name. The internal example lab uses `91.99.184.46`; substitute your own value everywhere `<HEADSCALE_HOST>` appears.

## What you will deploy

- A Headscale server listening on `:8080` (HTTP API) and `:9090` (metrics)
- A Headplane UI on `:3000`, configured to talk to Headscale
- Persistent bind-mount directories for Headscale state and Headplane data (no Docker named volumes)

The Compose files and configuration in this repo are located at:

```
neops-remote-lab/headscale/
  docker-compose.yml
  headplane.config.yaml
  config/
    config.yaml
    derp.yaml
```

!!! note "Where to run it"
    The services can run on the Remote Lab VM or on any reachable host. They do not have to share a host with the Remote Lab server.

## Prerequisites

- Docker and Docker Compose installed on the host that will run Headscale/Headplane.
- Network egress to reach client devices (Remote Lab subnet and peers).
- Optional but recommended for production: a reverse proxy or SSH access for port forwarding (see Access section below).

## Configure Headscale and Headplane (already provided)

This repository includes working templates:

### `config/config.yaml` — Headscale configuration

<!-- trace: headscale/config/config.yaml:13 -->
The repository commits `server_url: http://91.99.184.46:8080` -- this is the example lab's public IP and is not useful outside that environment. Before deploying for your own tailnet, edit `headscale/config/config.yaml:13` and replace the value with `http://<HEADSCALE_HOST>:8080` where `<HEADSCALE_HOST>` is the IP or DNS name clients reach Headscale at. This URL appears verbatim in every registered pre-auth key; changing it after clients register requires re-registering each node.

!!! warning "`server_url` must be reachable from every client"
    The URL in `server_url` is what Headscale tells clients to use for control-plane calls. Every Tailscale peer that joins the tailnet must be able to resolve and reach it. Get this wrong and registration silently times out.

DNS/MagicDNS and DERP settings are present and can be adjusted later.

### `headplane.config.yaml` — Headplane configuration

<!-- trace: headscale/docker-compose.yml:12 -->
Points to Headscale at `http://headscale:8080` (the Compose service name) and bind-mounts Headscale's `config.yaml` read-write so the Headplane UI can introspect and update configuration. Combined with `config_strict: false` in `headplane.config.yaml`, this means Headplane can mutate Headscale's live config.

!!! warning "Headplane can mutate Headscale config"
    The committed `docker-compose.yml` bind-mount at line 12 has no `:ro` flag, and `headplane.config.yaml` sets `config_strict: false`. Together, anyone with Headplane access can edit Headscale's configuration from the UI. Append `:ro` to the `config.yaml` bind-mount in `docker-compose.yml` if you want read-only behavior; restrict Headplane login accordingly (see the `cookie_secret` rotation warning below and the [Internal-trust warnings](../50-deployment/30-production.md#security) on Production).

!!! warning "Rotate the bundled `cookie_secret` before exposing Headplane"
    The committed `headplane.config.yaml` ships a placeholder `cookie_secret` so the UI starts on first run. Anyone with access to the public repo could forge Headplane sessions if you deploy with the bundled value. Generate a fresh secret per deployment:

    ```bash
    # In headscale/headplane.config.yaml: replace cookie_secret value with the output of:
    openssl rand -hex 32
    # And set cookie_secure: true once you front Headplane with TLS.
    ```

### `docker-compose.yml` — services and bind-mounts

- `headscale`: exposes `8080` and `9090`, persists `/var/lib/headscale` to `./lib`, mounts `./config` at `/etc/headscale`.
- `headplane`: exposes `3000`, persists `/var/lib/headplane` to `./headplane-data`, mounts the Headscale config for UI introspection.

You typically do not need to edit these files to get started beyond optionally changing `server_url` in `config/config.yaml`, and even that is optional if running locally.

## Start Headscale and Headplane

From the repository root, change into the Headscale directory and start services:

```bash
cd headscale
docker compose up -d

# Verify containers
docker ps --format 'table {{.Names}}\t{{.Image}}\t{{.Ports}}\t{{.Status}}'
```

Expected ports (host):

- Headscale API: `8080`
- Headscale metrics: `9090`
- Headplane UI: `3000`

## Accessing the services

### Direct access

You should be able to reach all services at `http://<VM_PUBLIC_IP>:<SERVICE_PORT>`. To open the Headplane UI on the example lab VM:

```
http://<HEADSCALE_HOST>:3000/admin
```

!!! warning "HTTP-only requires `cookie_secure: false`"
    When running Headscale/Headplane without HTTPS, the Headplane UI only works when `server.cookie_secure` in `headplane.config.yaml` is set to `false`. Flip it back to `true` when you put TLS in front (see Reverse-proxy section below).

### SSH port forwarding

If for some reason the services are not reachable through the VM's IP, use SSH port forwarding to reach Headplane via `localhost`:

```bash
ssh -L 3000:localhost:3000 root@<server_ip>
```

Then open Headplane at `http://127.0.0.1:3000/admin`.

### Reverse proxy + HTTPS + DNS (recommended for production)

Use a proper reverse proxy (Nginx/Caddy/Traefik) with HTTPS and a DNS name so `server_url` is a stable, secure URL like `https://headscale.example.com`. This is the recommended production setup; concrete recipes are not yet included in this repository and will be added later.

## Authenticate Headplane (no OIDC)

If you do not configure OIDC, generate a Headscale API key and use it to sign into Headplane:

```bash
docker exec headscale headscale apikeys create --expiration 999d
```

Copy the key and open Headplane at `http://<HEADSCALE_HOST>:3000/admin` (or via `localhost` with SSH port forwarding). Sign in using the API key.

!!! note
    You can add OIDC later; see examples in `headplane.config.yaml` and the Headplane docs.

## Manage users and auth keys

You can manage users and pre-auth keys via the Headscale CLI or the Headplane UI.

### Headplane UI (preferred to start)

Open the UI, add users, and generate/inspect pre-auth keys from the Users and Keys sections. If OIDC is configured, user management may be backed by your identity provider.

### Headscale CLI (concise equivalent)

```bash
# Create a user (owns machines and pre-auth keys)
docker exec headscale headscale users create <user>

# Create a pre-auth key for that user (valid 24h)
docker exec headscale headscale preauthkeys create -u <user> -e 24h

# Optional flags:
#   --ephemeral   create an ephemeral key (machine disappears when inactive)
#   -r            reusable key (can be used multiple times)
```

You can use such a key with the Tailscale client:

```bash
tailscale up --login-server <url> --auth-key <key>
```

…to skip interactive approval.

## Install Tailscale

Before any `tailscale` command in the next sections, the `tailscale` client must be present on the machine. Install it from the official source for your platform:

- **Ubuntu / Debian:** follow the signed-repo one-liner at <https://tailscale.com/download/linux>. Reproduced here for convenience:

    ```bash
    curl -fsSL https://tailscale.com/install.sh | sh
    ```

- **macOS:** install via the App Store, or `brew install --cask tailscale`.
- **Windows:** download the MSI installer from <https://tailscale.com/download/windows>.

Other platforms (NixOS, openSUSE, ChromeOS, container images) are documented at <https://tailscale.com/download>.

### Verify

```bash
tailscale version
```

Should print a `1.x.x` version number. If the binary is missing or you see a permission error, fix the install before proceeding.

## Connect clients (Tailscale)

You will connect two types of clients:

- The **Remote Lab host** (acts as a subnet router into the lab network).
- Other **peer devices** (laptops, CI, servers) that need to reach the lab subnet.

### Why `TS_ALLOW_INSECURE=1`?

This environment variable lets the Tailscale client talk to a Headscale `--login-server` over plain HTTP (no TLS) and skip certificate validation. Use it only while running without TLS — drop it once you put a reverse proxy with HTTPS in front.

### Remote Lab host (subnet router)

On the Remote Lab VM, run Tailscale and advertise the lab subnet. The default Containerlab management subnet is `192.168.121.0/24` (see [Topology Format](../10-concepts/40-topology-format.md)):

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://<HEADSCALE_HOST>:8080 \
  --accept-routes \
  --reset \
  --advertise-routes=192.168.121.0/24
```

!!! warning "`--reset` wipes existing Tailscale settings"
    The `--reset` flag clears any prior Tailscale configuration on this peer. Use it only on fresh machines or when you intend to rejoin from scratch. Drop the flag if you are reconnecting an already-configured node.

This prints an authentication URL such as:

```
To authenticate, visit:

    http://<HEADSCALE_HOST>:8080/register/8otva4j_QEUEmG1ZNjlShdgC

Success.
```

Approve the node using one of the following methods.

#### Headplane UI

Open Headplane → Machines → locate the pending registration → approve using the token shown above (e.g. `8otva4j_QEUEmG1ZNjlShdgC`).

#### Headscale CLI (from the host running Headscale)

```bash
docker exec headscale headscale nodes register --user <user> --key 8otva4j_QEUEmG1ZNjlShdgC
```

#### Approve the advertised subnet route

Node approval (above) is **not enough**. Headscale also needs to approve the advertised subnet route before traffic to `192.168.121.0/24` flows over the tailnet. After the node is registered:

```bash
# List the node and its advertised routes (look for the Remote Lab VM)
docker exec headscale headscale nodes list-routes

# Approve the lab subnet route (replace <node-id> with the node ID from `nodes list-routes`)
docker exec headscale headscale nodes approve-routes --identifier <node-id> --routes 192.168.121.0/24
```

Or via Headplane: Machines → select the Remote Lab VM → Routes → Approve.

!!! info "Headscale 0.26 CLI changes"
    Earlier headscale versions used `headscale routes list` and `headscale routes enable --route <id>`. Those subcommands were removed in headscale 0.26. Route management now lives under `headscale nodes`.

!!! warning "Symptom if you skip route approval"
    `tailscale status` shows the Remote Lab VM as green and `tailscale ping <remote-lab-host>` succeeds, but `ping <lab-container-IP>` from a peer just hangs. That means the node is reachable on the tailnet but the lab subnet route is not active — go back and approve the route.

### Peer devices

Run on each peer that needs access to the lab network:

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://<HEADSCALE_HOST>:8080 \
  --accept-routes \
  --reset
```

(See the same `--reset` warning above — drop the flag if you are reconnecting an already-configured peer.)

Approve each device with the same process as the subnet router (Headplane or CLI). Once approved, peers learn the lab subnet route from the Remote Lab host (after you approve routes).

## Remote Lab host: system settings

Ensure the Remote Lab VM is prepared for subnet routing:

```bash
# Disable Docker iptables interference when bridging to lab networks
sudo mkdir -p /etc/docker
echo '{"iptables": false}' | sudo tee /etc/docker/daemon.json
sudo systemctl restart docker || true

# Enable IPv4 forwarding (now)
sudo sysctl -w net.ipv4.ip_forward=1

# Persist across reboots via a sysctl drop-in (more reliable than editing /etc/sysctl.conf)
echo 'net.ipv4.ip_forward = 1' | sudo tee /etc/sysctl.d/99-tailscale.conf
sudo sysctl --system | grep ip_forward
```

!!! info "Why a drop-in file?"
    Editing `/etc/sysctl.conf` with `sed` is fragile — the line you target may be commented with leading whitespace, repeated, or absent entirely depending on the distribution. A drop-in under `/etc/sysctl.d/` always wins on reload and is unambiguous to audit (`ls /etc/sysctl.d/`).

## Verify end-to-end

Run these checks after the subnet router and at least one peer are connected and the route is approved:

1. **Tailnet membership.** On the peer:

    ```bash
    tailscale status
    ```

    Expected: a list of nodes including your peer (green) and the Remote Lab VM (green, with the advertised subnet listed under `subnets`).

2. **Tailnet reachability.** On the peer:

    ```bash
    tailscale ping <remote-lab-host>
    ```

    Expected: latency in tens of ms over `direct` or `derp` — pure tailnet round-trip, no lab traffic involved.

3. **Lab subnet reachability.** Spin up a topology on the Remote Lab VM (so a container has an address in `192.168.121.0/24`), find its IP via `docker inspect` or your topology, then on the peer:

    ```bash
    ping 192.168.121.<n>
    ```

    Expected: ICMP replies. If this hangs:

    - Re-check that the route is approved (`docker exec headscale headscale nodes list-routes` — the route for the Remote Lab VM should show as approved).
    - Re-check IPv4 forwarding is on the Remote Lab VM (`sysctl net.ipv4.ip_forward` → `1`).
    - Confirm `iptables` is set to `false` in `/etc/docker/daemon.json` and Docker has been restarted since.

## Data plane and ACLs

The VPN reachability you just verified hops through several layers. Knowing the path makes it easier to localize a failure:

```text
[ test runner / peer device ]
          |
          | 1. WireGuard tunnel (UDP)
          v
[ Headscale-coordinated tailnet ]
          |
          | 2. Subnet-route lookup
          v
[ Remote Lab VM 'ts0' interface ]
          |
          | 3. Linux routing (net.ipv4.ip_forward=1)
          v
[ clab-mgmt Docker bridge (192.168.121.0/24) ]
          |
          | 4. veth pair into container netns
          v
[ Container management interface (e.g. r1 eth1) ]
```

Notes on each hop:

1. The WireGuard tunnel is encrypted point-to-point; Headscale only coordinates the keys, it never carries data plane traffic.
2. The subnet route was approved earlier (`headscale nodes approve-routes ... --routes 192.168.121.0/24`).
3. IPv4 forwarding must be on. The `/etc/sysctl.d/99-tailscale.conf` drop-in earlier in this page configures it.
4. The bridge name and subnet (`clab-mgmt`, `192.168.121.0/24`) are Containerlab defaults for the Netlab `clab` provider; if you change them, update `--advertise-routes=` to match.

### Restricting peer access with ACLs

By default, every approved tailnet peer can reach every other peer on the advertised subnet. For shared deployments where some users should only reach lab subnets and not, say, the Remote Lab VM's SSH port, define a Headscale ACL policy. Headscale 0.26 reads policies from a JSON or HuJSON file referenced by `policy.path` in `config/config.yaml`.

Minimal sketch -- save as `headscale/config/acls.json`, set `policy.path: /etc/headscale/acls.json`, and restart Headscale (HuJSON is the more common Tailscale format; Headscale accepts either):

```text
{
  "tagOwners": {
    "tag:remote-lab-vm": ["lab-admin"],
    "tag:test-runner":   ["lab-admin"]
  },
  "acls": [
    {
      "action": "accept",
      "src":    ["tag:test-runner"],
      "dst":    ["192.168.121.0/24:*"]
    }
  ]
}
```

Validate before applying (the exact subcommand varies by Headscale version -- check `headscale policy --help` first):

```bash
docker exec headscale headscale policy check --policy-file /etc/headscale/acls.json
docker compose restart headscale
```

Tag the relevant nodes via Headplane or `headscale nodes tag --identifier <id> --tags tag:test-runner` so the policy matches them. See the [Tailscale ACL reference](https://tailscale.com/kb/1018/acls) for full policy syntax (Headscale aims to track the same grammar).

## Notes, tips, and next steps

- **Where to run:** Headscale/Headplane can run on the Remote Lab VM or elsewhere; the only requirement is that clients can reach `server_url`.
- **TLS:** If you enable TLS or use a reverse proxy with HTTPS, update `server_url` to `https://…`, configure certs accordingly, and remove `TS_ALLOW_INSECURE=1` from the `tailscale up` invocations.
- **DERP:** For constrained NATs, consider enabling embedded DERP (requires TLS) or referencing external DERP maps; see comments in `config/config.yaml`.
- **Pre-auth keys:** Instead of interactive approval, you may create reusable or ephemeral pre-auth keys via the Headscale CLI and pass them to clients with `tailscale up --auth-key=<key>`.

Troubleshooting pointers:

- Check container logs: `docker logs headscale`, `docker logs headplane`.
- Verify Headscale health: open `http://127.0.0.1:9090/metrics` (or via SSH tunnel).
- Confirm routes on peers: `ip route | grep 192.168.121.0/24`.

## Quick command summary

A copy-and-paste-friendly recap. See the linked sections above for context and warnings.

**Start services** ([§ Start Headscale and Headplane](#start-headscale-and-headplane))

```bash
cd headscale
docker compose up -d
```

**Headplane login (no OIDC)** ([§ Authenticate Headplane (no OIDC)](#authenticate-headplane-no-oidc))

```bash
docker exec headscale headscale apikeys create --expiration 999d
```

**Create user and pre-auth key** ([§ Manage users and auth keys](#manage-users-and-auth-keys))

```bash
docker exec headscale headscale users create <user>
docker exec headscale headscale preauthkeys create -u <user> -e 24h
```

**Remote Lab VM (subnet router)** ([§ Remote Lab host (subnet router)](#remote-lab-host-subnet-router))

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://<HEADSCALE_HOST>:8080 \
  --accept-routes \
  --advertise-routes=192.168.121.0/24
```

**Approve interactive registration** ([§ Headscale CLI](#headscale-cli-from-the-host-running-headscale))

```bash
docker exec headscale headscale nodes register --user <user> --key <token>
```

**Approve subnet route** ([§ Approve the advertised subnet route](#approve-the-advertised-subnet-route))

```bash
docker exec headscale headscale nodes list-routes
docker exec headscale headscale nodes approve-routes --identifier <node-id> --routes 192.168.121.0/24
```

**Peers (accept routes)** ([§ Peer devices](#peer-devices))

```bash
TS_ALLOW_INSECURE=1 tailscale up \
  --login-server http://<HEADSCALE_HOST>:8080 \
  --accept-routes
```
