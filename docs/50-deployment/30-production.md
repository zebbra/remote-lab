---
page_purpose: how-to
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: advanced
---

# Production Deployment

This page covers running the Remote Lab server as a persistent, monitored service. For server CLI flags and environment variables, see the [Configuration](../20-server/20-configuration.md) reference. For day-to-day operations and troubleshooting, see [Administration](../20-server/30-administration.md).

## Running as a systemd service

The recommended way to run the server on a production host is via a systemd unit. This gives you automatic restarts, journal-based logging, and clean signal handling.

### Example unit file

Create `/etc/systemd/system/neops-remote-lab.service`:

```ini
[Unit]
Description=neops Remote Lab Manager
After=network-online.target docker.service
Wants=network-online.target
Requires=docker.service

[Service]
Type=simple
User=labuser
Group=labuser
WorkingDirectory=/home/labuser
ExecStart=/home/labuser/.local/bin/neops-remote-lab --host 0.0.0.0 --port 8000 --log-level INFO
Restart=on-failure
RestartSec=10
TimeoutStopSec=120

# Clean shutdown: the server handles SIGTERM gracefully,
# tearing down any running lab before exiting.
KillSignal=SIGTERM
KillMode=mixed

# Environment
Environment="PATH=/home/labuser/.local/bin:/usr/local/bin:/usr/bin:/bin"

[Install]
WantedBy=multi-user.target
```

Adapt the `User`, `WorkingDirectory`, and `ExecStart` path to your environment. If you installed via `uv` or `pipx`, point `ExecStart` to the correct binary location.

!!! warning "TimeoutStopSec"
    Set `TimeoutStopSec` high enough for the server to tear down any running Netlab topology. `netlab down --cleanup` can take over a minute for complex topologies. If systemd kills the process before cleanup finishes, you may end up with stale containers that require manual removal.

### Enable and start

```bash
sudo systemctl daemon-reload
sudo systemctl enable neops-remote-lab
sudo systemctl start neops-remote-lab

# Verify
sudo systemctl status neops-remote-lab
journalctl -u neops-remote-lab -f
```

### Log output

The server writes structured logs to stdout, which systemd captures in the journal. Use `journalctl` to view them:

```bash
# Recent logs
journalctl -u neops-remote-lab --since "10 minutes ago"

# Follow live
journalctl -u neops-remote-lab -f
```

For file-based logging, provide a custom logging config via `--log-config` that adds a `RotatingFileHandler`. See the [Configuration](../20-server/20-configuration.md#custom-logging-configuration) page for an example.

## Reverse proxy considerations

The server binds to `0.0.0.0:8000` by default. In production, you typically front it with a reverse proxy (Nginx, Caddy, or Traefik) to handle TLS termination and access control.

Key points for your proxy configuration:

- **Timeouts**: Lab acquisition (`POST /lab`) triggers `netlab up`, which can take several minutes. Set your proxy's read/write timeout to at least 600 seconds to avoid cutting off long-running requests.
- **Request body size**: Topology files are uploaded as multipart form data. The files are typically small (under 1 MB), but set a reasonable body size limit (e.g., 10 MB) to accommodate extra files.
- **Websockets**: Not used by Remote Lab -- standard HTTP proxying is sufficient.
- **Headers**: The proxy must forward `X-Session-ID` headers unchanged. This is the session identity mechanism for all `/lab/*` endpoints.

### Example Nginx location block

```nginx
location / {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;

    # Long timeout for lab acquisition
    proxy_read_timeout 600s;
    proxy_send_timeout 600s;

    # Body size for topology uploads
    client_max_body_size 10m;
}
```

## TLS / HTTPS

Remote Lab does not terminate TLS itself. If your deployment requires encrypted transport (recommended for anything beyond a local LAN), handle TLS at the reverse proxy layer.

If you are running the server behind a [Headscale VPN](20-headscale-vpn.md), the tailnet provides encrypted point-to-point tunnels, so TLS at the application layer is optional. This is the typical setup: the server runs plain HTTP, reachable only through the VPN mesh.

For internet-facing deployments (not recommended -- see Security below), use a reverse proxy with TLS certificates from Let's Encrypt or your internal CA.

### End-to-end nginx TLS recipe

The concern: terminate TLS at nginx, keep the server bound to localhost, and use a systemd drop-in so the service will not start before nginx has a live cert.

**1. Restrict the server to localhost.** Create `/etc/systemd/system/neops-remote-lab.service.d/bind-local.conf`:

```ini title="/etc/systemd/system/neops-remote-lab.service.d/bind-local.conf"
[Service]
# Override ExecStart to bind only to 127.0.0.1 — external traffic goes through nginx.
ExecStart=
ExecStart=/home/labuser/.local/bin/neops-remote-lab --host 127.0.0.1 --port 8000 --log-level INFO
```

Apply with `sudo systemctl daemon-reload && sudo systemctl restart neops-remote-lab`. (The empty first `ExecStart=` is required — systemd concatenates otherwise.)

**2. Obtain a certificate.** Use Let's Encrypt via certbot or your internal CA:

```bash
sudo certbot certonly --nginx -d lab.example.com
```

**3. nginx site config** at `/etc/nginx/sites-available/remote-lab`:

```nginx title="/etc/nginx/sites-available/remote-lab"
server {
    listen 443 ssl http2;
    server_name lab.example.com;

    ssl_certificate     /etc/letsencrypt/live/lab.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/lab.example.com/privkey.pem;
    ssl_protocols       TLSv1.2 TLSv1.3;

    # Long timeouts — netlab up can take several minutes
    proxy_read_timeout  600s;
    proxy_send_timeout  600s;
    client_max_body_size 10m;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        # X-Session-ID must pass through unchanged.
    }
}

server {
    listen 80;
    server_name lab.example.com;
    return 301 https://$host$request_uri;
}
```

Enable, test, reload:

```bash
sudo ln -s /etc/nginx/sites-available/remote-lab /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

**Why this shape?** Terminating at nginx lets the Python server stay plain-HTTP (simpler, no cert handling inside the app), while the loopback bind stops a missing firewall rule from accidentally exposing port 8000. Clients use `https://lab.example.com`; the tailnet/VPN assumption from Security applies unchanged for workloads that never touch the public certificate path.

If you run the server behind Headscale/Tailscale instead, skip this recipe — the tailnet already encrypts inter-peer traffic and the plain-HTTP bind is the intended posture.

## Monitoring

### Liveness probe: `GET /healthz`

Returns `204 No Content` with no body when the server is alive. Use this for load balancer health checks, systemd watchdog integration, or external monitoring tools.

```bash
curl -sf http://localhost:8000/healthz && echo "UP" || echo "DOWN"
```

The handler is lightweight and does not emit application-level logs, but uvicorn's access log still records every request because the server starts uvicorn with `access_log=True` (`neops_remote_lab/__main__.py`). If a frequent prober (e.g. a Kubernetes liveness probe firing every 2 seconds) floods the journal, suppress those entries with a `logging.Filter` attached to the `uvicorn.access` logger:

```python
# /etc/remote-lab/healthz_filter.py
import logging

class SuppressHealthz(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        # uvicorn.access records the path in record.args[2]
        try:
            path = record.args[2]
        except (TypeError, IndexError):
            return True
        return path != "/healthz"
```

Wire it in via your `--log-config` YAML:

```yaml
filters:
  suppress_healthz:
    "()": healthz_filter.SuppressHealthz
loggers:
  uvicorn.access:
    filters: [suppress_healthz]
```

See [Configuration -- Custom Logging Configuration](../20-server/20-configuration.md#custom-logging-configuration) for the surrounding `--log-config` structure.

### Debug health: `GET /debug/health`

Returns a JSON payload with uptime, session count, and queue length. Useful for dashboards and alerting.

```bash
curl -s http://localhost:8000/debug/health | jq .
```

```json
{
  "status": "ok",
  "timestamp": 1716812096.123,
  "uptime": 3600.5,
  "sessions": 1,
  "queue_length": 1
}
```

### Integration with monitoring systems

- **Prometheus/Grafana**: Use a blackbox exporter to probe `/healthz`, or scrape `/debug/health` with a custom exporter that exposes `uptime`, `sessions`, and `queue_length` as gauges.
- **Uptime Kuma / Healthchecks.io**: Point an HTTP check at `http://<host>:8000/healthz` expecting a 204 response.
- **systemd watchdog**: Add `WatchdogSec=30` to the unit file and configure the server to send `sd_notify` pings (not built in -- requires a wrapper script or a systemd notify socket proxy).

### Prometheus: scrape `/debug/health`

<!-- trace: neops_remote_lab/server.py:116 -->
The server exposes `/debug/health` as a structured JSON document (`status`, `uptime`, `sessions`, `queue_length`) which is a natural target for a thin exporter or for the Prometheus `json_exporter` community module. A minimal `json_exporter` scrape config:

```yaml title="/etc/prometheus/prometheus.yml (excerpt)"
scrape_configs:
  - job_name: remote-lab
    metrics_path: /probe
    params:
      module: [ remote_lab_health ]
    static_configs:
      - targets: [ "http://lab-host:8000/debug/health" ]
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: json-exporter:7979
```

With matching `json_exporter` config:

```yaml title="/etc/json_exporter/config.yml"
modules:
  remote_lab_health:
    metrics:
      - name: remote_lab_uptime_seconds
        path: '{ .uptime }'
        help: "Seconds since Remote Lab server started"
      - name: remote_lab_sessions_total
        path: '{ .sessions }'
        help: "Tracked sessions (WAITING + ACTIVE)"
      - name: remote_lab_queue_length
        path: '{ .queue_length }'
        help: "Sessions currently in the FIFO queue"
```

<!-- trace: neops_remote_lab/server.py:95 -->
The server applies two distinct staleness timeouts: `WAITING` sessions are trimmed after `_WAITING_SESSION_TIMEOUT` (default **600 s**, `server.py:95`), and the currently `ACTIVE` session is trimmed after `_ACTIVE_SESSION_STALE` (default **300 s**, `server.py:96`) from its last `last_seen_at` update. Since `queue_length` is dominated by `WAITING` entries (there is at most one `ACTIVE`), an alert on `remote_lab_queue_length > N` should allow at least **600 s** of grace before firing, or it will fire on a queue the server is about to trim on its own.

### Grafana panel sketch

A compact panel set that surfaces the useful signals without overfitting to this service's specifics:

| Panel | Metric | Thresholds |
|-------|--------|------------|
| Uptime | `remote_lab_uptime_seconds` | Sparkline — obvious dips on restart |
| Queue depth | `remote_lab_queue_length` | Yellow at 3, red at 10 — tuning target is session-timeout-dependent |
| Session throughput | `rate(remote_lab_sessions_total[5m])` | Reference value; not alertable |
| Liveness | `probe_success` (from blackbox exporter on `/healthz`) | Red for any missed probe |

Save the dashboard JSON alongside your Prometheus config so it is reproducible.

### Log shipping: journald → Loki

The systemd unit writes structured logs to the journal. To forward them to Loki, install `promtail` on the host and point it at the journal:

```yaml title="/etc/promtail/config.yml (journal source)"
scrape_configs:
  - job_name: journal-remote-lab
    journal:
      matches: _SYSTEMD_UNIT=neops-remote-lab.service
      max_age: 12h
      labels:
        job: remote-lab
        host: ${HOSTNAME}
    relabel_configs:
      - source_labels: ['__journal__systemd_unit']
        target_label: 'unit'
```

Useful queries once the stream is in Loki:

```logql
# Error rate over time
sum(rate({job="remote-lab"} |= "ERROR" [5m]))

# Session promotions
{job="remote-lab"} |= "promoted to ACTIVE"

# 423 Locked retries (server-emitted log line when try_acquire returns None)
{job="remote-lab"} |= "Lab currently busy"
```

## Security

<!-- trace: neops_remote_lab/client.py:1 -->
!!! warning "Internal-trust service"
    <!-- trace: neops_remote_lab/client.py -->
    As of this version, `REMOTE_LAB_TOKEN` and Bearer auth are commented out in `client.py`; the only access boundary on `/lab/*` endpoints is the `X-Session-ID` header of the currently `ACTIVE` session. Deploy only inside networks you trust. The guidance below describes the VPN and firewall posture that makes this trust assumption safe.

Remote Lab uses an **internal trust model**. There is no authentication layer -- the `REMOTE_LAB_TOKEN` / Bearer auth code path in the client is commented out and the server has no corresponding handler, so the variable name is a placeholder, not active auth. The only access boundary is the `X-Session-ID` header, which must belong to an `ACTIVE` session.

This means:

- **Do not expose the server to the public internet.** Anyone who can reach the HTTP port can create sessions and control Netlab.
- **Run behind a VPN.** The intended deployment model is a [Headscale/Tailscale](20-headscale-vpn.md) mesh where only authorized peers can reach the server.
- **Firewall the port.** If VPN is not an option, use host-level firewall rules (`ufw`, `iptables`) to restrict access to known CI runner IPs.

See the [Architecture](../10-concepts/10-architecture.md#trust-model) section for the full trust model explanation.

### Secret management

The server itself does not read operator secrets today — `REMOTE_LAB_TOKEN` is a placeholder for a future auth path. Where secrets do enter production deployments:

- **Headplane `cookie_secret`** (see [Headscale VPN](20-headscale-vpn.md#headplaneconfigyaml--headplane-configuration)) — rotate on every deploy, never commit.
- **Headscale pre-auth keys** — create short-lived, avoid reusable keys in CI.
- **Netlab `iourc.txt`** / Cisco IOL license — treat as vendor-restricted and do not store in the repo.
- **Environment variables consumed by your own monkey-patched hooks or `--log-config`** — whatever you inject.

For any of these, prefer systemd-native secret delivery over plain `.env` files:

**`EnvironmentFile=` with locked-down permissions** — the simplest option:

```ini title="/etc/systemd/system/neops-remote-lab.service.d/secrets.conf"
[Service]
EnvironmentFile=/etc/neops-remote-lab/env
```

```bash
sudo install -d -m 0750 -o root -g labuser /etc/neops-remote-lab
sudo install -m 0640 -o root -g labuser /path/to/env /etc/neops-remote-lab/env
sudo systemctl daemon-reload && sudo systemctl restart neops-remote-lab
```

`0640` + group `labuser` means only root and the service user can read the file; `auditd` watches on the directory will catch rotations.

**`LoadCredential=` for ephemeral per-start secrets** (systemd 247+):

```ini title="/etc/systemd/system/neops-remote-lab.service.d/secrets.conf"
[Service]
LoadCredential=headplane_cookie:/etc/neops-remote-lab/headplane_cookie
# The credential is available as $CREDENTIALS_DIRECTORY/headplane_cookie
# inside the unit's exec environment, visible to no other process.
```

This is preferable when the secret is actually loaded once at startup — the file is never readable by other units on the host.

**`.env` hygiene.** If you still use `.env` for development convenience:

```bash
chmod 0600 .env
chown labuser:labuser .env
# Ensure .env is in .gitignore AND .dockerignore.
```

A `.env` with `0644` permissions on a shared host is indistinguishable from no secret management at all.

**Rotating the Headplane `cookie_secret`** without downtime of the Remote Lab server:

```bash
cd headscale
# Generate fresh secret
openssl rand -hex 32 > /tmp/cookie_secret.new
# Edit headplane.config.yaml in-place (swap cookie_secret value), then:
docker compose up -d --force-recreate headplane
rm /tmp/cookie_secret.new
```

Headplane-side only — the Remote Lab server is unaffected.

## Capacity and scaling

Remote Lab is deliberately simple: one server, one host, one lab at a time. The [one-lab-per-host constraint](../10-concepts/10-architecture.md#one-lab-per-host-constraint) is not a tuning knob -- it is an architectural invariant inherited from Netlab. That shapes everything below.

### Throughput

A single server serves one topology at a time. Concurrent testers share the server by time-slicing topology lifetimes: at most one session is `ACTIVE`; the rest queue. Wall-clock throughput is bounded by how long each test run holds the lab plus Netlab's teardown/rebuild cost between different topologies. Shared topologies (`reuse_lab=True`) skip the rebuild cost and drop throughput cost close to zero.

Queue depth is bounded by the waiting-session timeout. A session that has been `WAITING` without activity for longer than the configured window is dropped by the cleanup loop; clients see a `RuntimeError` / timeout. See [Configuration -- Server Constants](../20-server/20-configuration.md#server-constants) for the current default.

### When to add another host

Add a second host (each with its own Remote Lab server) when the single-server symptoms start to hurt:

- Queue depth is routinely greater than the number of concurrent CI jobs you want to serve in parallel.
- `REMOTE_LAB_SESSION_TIMEOUT` errors appear in test logs because jobs wait longer than the session timeout.
- Wall-clock test time on shared CI is dominated by queue waiting rather than actual test execution.

Deploy a second VM with the same Netlab/Containerlab/Remote Lab stack and point a subset of clients at its `REMOTE_LAB_URL`. The hosts operate independently.

### What "federation" is not

Remote Lab does not support a federated multi-host mode. There is no shared session queue, no coordinator that routes clients to a free host, and no discovery protocol between servers. Each host is a standalone deployment; clients target exactly one `REMOTE_LAB_URL`. If you need cross-host routing, build it outside Remote Lab (for example: a simple front-door that picks the least-loaded host's URL based on `/debug/health`).

### Scaling knobs on a single host

Within a single host, the useful levers are:

- **VM RAM and CPU** -- Netlab/Containerlab spawn one container per topology node. RAM sets the ceiling on node count and image size (e.g. FRR vs. Nokia SR Linux vs. Arista cEOS). CPU matters during `netlab up` and during Ansible configuration passes.
- **Network throughput** -- remote tests that SSH into many nodes or collect large operational-state dumps will saturate the VM's uplink before they saturate CPU. Prefer a host with predictable network bandwidth over one with peak-burst allowance.
- **Netlab / Containerlab image cache** -- first-time lab acquisition is dominated by `docker pull` for missing container images. Pre-warm the cache on the VM by pulling the images you expect to use; subsequent acquisitions only pay for configuration, not download.

### Resource sizing

These are operator-experience sizing recommendations, not numbers extracted from the code. Use them to pick an initial VM and re-measure on your own workload.

| Topology class | Nodes | CPU cores | RAM | Disk (image cache + working dirs) |
|----------------|------:|----------:|----:|-----------------------------------|
| Tiny (smoke / examples) | 2-4 | 2 | 4 GB | 20 GB |
| Small (tutorial / review) | 5-8 | 4 | 8 GB | 40 GB |
| Medium (CI mainline) | 10-20 | 8 | 16 GB | 80 GB |
| Large (DC / multi-VRF) | 30-60 | 16 | 32 GB | 160 GB |

Image footprint is the dominant RAM factor:

| Device kind | Typical RAM per node |
|-------------|---------------------|
| FRR | ~150 MB |
| Nokia SR Linux | ~400 MB |
| Arista cEOS | ~1.5 GB |
| Cisco IOL / IOL-L2 | ~400 MB |
| Juniper cRPD | ~500 MB |

Typical `netlab up` wall-clock (cold cache, no reuse):

| Device kind | 2-node `netlab up` | 10-node `netlab up` |
|-------------|-------------------:|--------------------:|
| FRR | ~30 s | ~1-2 min |
| Nokia SR Linux | ~1 min | ~3-4 min |
| Arista cEOS | ~2-3 min | ~6-8 min |
| Cisco IOL | ~1-2 min | ~4-6 min |

Warm cache halves the small-topology times; it is the single biggest wall-clock lever. Pre-pull images on the host with `docker pull` matching each `defaults.devices.<kind>.clab.image` value before accepting production traffic.

## Backup considerations

The Remote Lab server itself is stateless between restarts -- session state and lab state live in memory and are rebuilt on startup. However, there are two categories of state worth backing up:

### Headscale state

If you run a [Headscale VPN](20-headscale-vpn.md) alongside the Remote Lab server, the Headscale database contains node registrations, pre-auth keys, and ACL configuration. The repository's `headscale/docker-compose.yml` uses **bind mounts** rather than Docker named volumes -- the SQLite database lives on the host at `headscale/lib/db.sqlite` (the path inside the container is `/var/lib/headscale/db.sqlite`, configured in `headscale/config/config.yaml`).

```bash
# Inspect the bind-mount directory
ls headscale/lib/
```

<!-- trace: headscale/config/config.yaml:165 -->
Headscale enables WAL mode (`write_ahead_log: true` in `config/config.yaml`), so a naive `cp` while Headscale is writing can capture an inconsistent snapshot. Pick one of the two patterns below:

**Cold backup** (simplest -- requires brief downtime):

```bash
cd headscale
docker compose stop headscale
tar czf "../headscale-backup-$(date +%F).tgz" lib/
docker compose start headscale
```

**Live safe backup** (uses SQLite's online backup API -- no downtime):

```bash
docker exec headscale sqlite3 /var/lib/headscale/db.sqlite \
    ".backup '/var/lib/headscale/backup.db'"
cp headscale/lib/backup.db "./headscale-backup-$(date +%F).db"
```

Include the chosen procedure in your regular backup schedule. Losing Headscale state means re-registering all nodes.

**Restore from cold backup:**

```bash
cd headscale
docker compose stop headscale
rm -rf lib
tar xzf "../headscale-backup-2026-01-15.tgz"
# Verify structure before restart
ls lib/db.sqlite lib/private.key 2>/dev/null || { echo "restore archive incomplete"; exit 1; }
docker compose start headscale
```

**Restore from live-safe backup:**

```bash
cd headscale
docker compose stop headscale
cp "../headscale-backup-2026-01-15.db" lib/db.sqlite
docker compose start headscale
```

**Verification after either restore** — confirm the Headscale daemon came back healthy and rediscovered its state:

```bash
# Container is up and serving
docker compose ps headscale     # State: Up
docker logs --tail 50 headscale | grep -E "listening|error"

# API health (port 8080 from docker-compose.yml:32)
curl -sf http://127.0.0.1:8080/health && echo OK

# State survived: users and pre-auth keys visible
docker exec headscale headscale users list
docker exec headscale headscale preauthkeys list -u <user>

# Nodes can still register and the existing tailnet is intact
docker exec headscale headscale nodes list
```

If any step fails, do not start approving new registrations — the failure will compound. Re-try the restore with the prior backup archive and escalate if that also fails.

### Netlab configuration

The host-level Netlab configuration (`~/.netlab.yml`) and any custom topology files are worth preserving. These are typically checked into version control but may contain host-specific overrides (image paths, provider settings) that are not in the repo.

### What you do not need to back up

- **Server session state**: Rebuilt on startup. Sessions are ephemeral.
- **Lock files**: Located in `/tmp/`. Automatically cleaned up on shutdown and recovered on startup.
- **Lab working directories**: Temporary directories created per topology run. Cleaned up by the server and by `atexit` hooks.
