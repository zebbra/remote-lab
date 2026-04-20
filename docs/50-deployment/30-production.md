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

## Backup considerations

The Remote Lab server itself is stateless between restarts -- session state and lab state live in memory and are rebuilt on startup. However, there are two categories of state worth backing up:

### Headscale state

If you run a [Headscale VPN](20-headscale-vpn.md) alongside the Remote Lab server, the Headscale database contains node registrations, pre-auth keys, and ACL configuration. The repository's `headscale/docker-compose.yml` uses **bind mounts** rather than Docker named volumes -- the SQLite database lives on the host at `headscale/lib/db.sqlite` (the path inside the container is `/var/lib/headscale/db.sqlite`, configured in `headscale/config/config.yaml`).

```bash
# Inspect the bind-mount directory
ls headscale/lib/
```

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

### Netlab configuration

The host-level Netlab configuration (`~/.netlab.yml`) and any custom topology files are worth preserving. These are typically checked into version control but may contain host-specific overrides (image paths, provider settings) that are not in the repo.

### What you do not need to back up

- **Server session state**: Rebuilt on startup. Sessions are ephemeral.
- **Lock files**: Located in `/tmp/`. Automatically cleaned up on shutdown and recovered on startup.
- **Lab working directories**: Temporary directories created per topology run. Cleaned up by the server and by `atexit` hooks.
