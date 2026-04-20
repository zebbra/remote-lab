---
page_purpose: how-to
personas_served: [devops-engineer]
difficulty_level: intermediate
---

# Administration

Three surfaces cover most of on-call work: the journal (what the service just said), the `sessions` and `/debug/health` endpoints (what the service thinks its state is), and the systemd unit (what the service is supposed to be doing). The rest of the page is startup behavior, single-instance guard mechanics, the upgrade/rollback runbook, and a troubleshooting table for the faults that actually show up in practice.

## Starting the Server

### From PyPI install

```bash
neops-remote-lab --host 0.0.0.0 --port 8000 --log-level info
```

### From source (development)

```bash
uv sync --group dev
uv run neops-remote-lab --host 0.0.0.0 --port 8000 --log-level info
```

### Expected startup output

On a successful start, the server logs:

1. Logging configuration loaded
2. Startup cleanup of stale Netlab instances (from any previous crashed run)
3. Session cleanup background task started
4. Uvicorn listening on the configured host and port

### Pre-flight checks

Before serving requests, the server verifies that the `netlab` CLI is available in `PATH` and responds to `netlab version`. If either check fails, the server exits with an error message and a link to the [Netlab installation guide](https://netlab.tools/install/ubuntu/).

## Startup Cleanup

On every startup, the server performs automatic cleanup of stale Netlab instances from previous runs. This calls `LabManager.cleanup` with `default_instance=True`, which tears down any `default` Netlab instance left behind by a crashed or force-killed server process.

<!-- trace: neops_remote_lab/server.py:47 -->
On a clean start, the startup cleanup logs two INFO lines -- `Performing startup cleanup of stale netlab instances...` and `Startup cleanup completed successfully` (`server.py:44-47`). A WARNING (`Startup cleanup encountered an error ...`) is emitted only if the cleanup call raises an unexpected exception (`server.py:49`). Either path, the server continues startup.

## Single-Instance Guard

Only one Remote Lab server process can run per host. The server enforces this with a file lock.

### How it works

On startup, the server acquires an exclusive lock on a file in the system temp directory:

- **Lock file:** `<tempdir>/neops_remote_lab_server.lock`
- **Metadata file:** `<tempdir>/neops_remote_lab_server.meta.json`

If the lock is already held by a live process, the server prints diagnostic details about the running instance and exits with code 1.

### Instance metadata

The metadata file contains information about the running server:

```json
{
  "pid": 12345,
  "user": "labuser",
  "host": "lab-vm-01",
  "started_at": 1716812096.123,
  "port": 8000,
  "host_bind": "0.0.0.0",
  "log_level": "INFO",
  "log_config": "logging_config.yaml",
  "version": "0.5.0",
  "cwd": "/home/labuser/remote-lab",
  "cmd": "neops-remote-lab --host 0.0.0.0 --port 8000"
}
```

### Stale lock recovery

If the lock is held but the PID recorded in the metadata file is no longer alive, the server detects the stale state, removes the metadata file, and re-attempts lock acquisition. If re-acquisition succeeds, the server proceeds normally.

### Manual recovery

If automatic recovery fails (e.g., the metadata file was deleted but the lock persists), manually remove the lock file:

```bash
# Find the lock file
ls /tmp/neops_remote_lab_server.*

# Verify no server process is running
pgrep -f neops-remote-lab

# Remove stale files
rm /tmp/neops_remote_lab_server.lock /tmp/neops_remote_lab_server.meta.json
```

On exit (clean shutdown or Ctrl+C), the server releases the lock and removes the metadata file automatically.

## Monitoring

### Liveness probe: GET /healthz

Returns `204 No Content` with no body if the server is up. Use this for load balancer health checks or container liveness probes. The handler does not emit application-level logs; uvicorn's access log still records the request (`access_log=True` in `__main__.py`). To suppress access logs for `/healthz` specifically, see [Production -- Liveness probe](../50-deployment/30-production.md#liveness-probe-get-healthz).

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz
# 204
```

### Debug health: GET /debug/health

Returns a JSON object with runtime statistics. Useful during development and incident investigation.

```bash
curl -s http://localhost:8000/debug/health | jq .
```

```json
{
  "status": "ok",
  "timestamp": 1716812096.123,
  "uptime": 3600.5,
  "sessions": 2,
  "queue_length": 2
}
```

Key fields:

- `uptime` -- Seconds since server started. Useful for detecting unexpected restarts.
- `sessions` -- Total tracked sessions (both `WAITING` and `ACTIVE`).
- `queue_length` -- Sessions currently in the FIFO queue.

### Checking session state

To inspect the active session directly:

```bash
curl -s http://localhost:8000/active-session | jq .
```

See the [REST API reference](10-rest-api.md) for the full set of session and lab status endpoints.

## Upgrade and rollback

A versioned Remote Lab server is upgraded by pinning a new release tag, reinstalling, and restarting the systemd unit. The steps below assume the systemd unit from [Production — Running as a systemd service](../50-deployment/30-production.md#running-as-a-systemd-service).

!!! warning "Startup cleanup drops in-flight work"
    <!-- trace: neops_remote_lab/server.py:44 -->
    On every restart, the server runs `LabManager.cleanup(default_instance=True)` (`server.py:44-47`), which tears down any running Netlab instance. Sessions live in memory and are **not** persisted — they do not survive restart. A restart during active CI jobs drops their `ACTIVE` session silently; the CI client will see its next request fail with `404 Not Found`. Schedule upgrades during a maintenance window, or verify `GET /active-session` returns `404` before restarting.

### Upgrade procedure

```bash
# 1. Pick a target version (tag or PyPI release).
#    Confirm the version bumps cleanly by reading CHANGELOG first.

# 2. Drain — ensure no sessions are active.
curl -sf http://localhost:8000/active-session >/dev/null && \
    echo "Refusing to upgrade: active session present" && exit 1

# 3. Install the new version.
#    neops-remote-lab is proprietary (see pyproject.toml:7). pipx-install from
#    the PyPI-compatible index your organization publishes to — substitute the
#    version literal and --index-url for your environment:
sudo -u labuser pipx install --force \
    --index-url https://<your-internal-index>/simple/ \
    "neops-remote-lab==<your-version>"

#    Or from source at a git tag:
sudo -u labuser bash -c '
    cd /home/labuser/neops-remote-lab &&
    git fetch --tags &&
    git checkout <your-version> &&
    uv sync --group dev
'

# 4. Restart the service.
sudo systemctl restart neops-remote-lab

# 5. Smoke test.
sleep 3
curl -sf http://localhost:8000/debug/health | jq .
# Expected: {"status":"ok", "uptime":<small_number>, ...}
```

<!-- trace: neops_remote_lab/server.py:116 -->
The smoke test confirms the new binary came up, the lock file was acquired, and the API is responding. The `uptime` field comes from `/debug/health` at `server.py:116-128`; `/healthz` at `server.py:471-476` is the quieter sibling that returns `204 No Content` and can be used in load-balancer probes once you've confirmed the richer endpoint above.

### Rollback procedure

If the smoke test fails or production traffic surfaces a regression, roll back to the previous known-good tag:

```bash
# 1. Install the previous version.
sudo -u labuser pipx install --force "neops-remote-lab==0.5.0"
#    Or from source:
sudo -u labuser bash -c '
    cd /home/labuser/neops-remote-lab &&
    git checkout v0.5.0 &&
    uv sync --group dev
'

# 2. Restart.
sudo systemctl restart neops-remote-lab

# 3. Re-run the smoke test (same curl as above).
```

Rollback carries the same in-flight-session warning as upgrade.

!!! warning "When rollback itself fails"
    Two scenarios are common and each has a different exit:
    (1) **Install of the previous version fails** (e.g., network error, yanked wheel, dependency resolution regression). Do NOT `systemctl restart` — the current binary is still running. Diagnose the install failure, fix it, or install a different known-good tag.
    (2) **Install succeeds but the previous version won't start** (e.g., config file on disk has since been updated for the new schema). The service will flap on `Restart=on-failure`. Stop the service explicitly (`sudo systemctl stop neops-remote-lab`), clear the broken install (`pipx uninstall neops-remote-lab`), revert any config-file changes the upgrade made, and reinstall a tagged version manually rather than chasing the restart loop.

If neither the new nor the previous version starts, treat it as an incident and fall back to the last known-good snapshot (see [Production — Backup considerations](../50-deployment/30-production.md#backup-considerations)).

### Capture diagnostics before upgrade

Useful to grab *before* restarting, so you can compare post-upgrade:

```bash
journalctl -u neops-remote-lab --since "1 hour ago" > /tmp/pre-upgrade.log
curl -s http://localhost:8000/debug/health > /tmp/pre-upgrade-health.json
```

If the upgrade surfaces problems, these are the baseline you compare against the first few hours of logs after the new version starts.

## Graceful Shutdown

The server handles `SIGTERM` and `SIGINT` for graceful shutdown. On receiving either signal:

1. The shutdown event is set, stopping the cleanup background task.
2. All remaining sessions are deleted.
3. `LabManager.cleanup` runs a final teardown of any running lab.
4. The lock file and metadata file are removed.

During shutdown, session deletion requests from clients are handled gracefully -- sessions are removed without failing even if lab cleanup encounters errors.

## Troubleshooting

### Server won't start

| Check | Resolution |
|-------|------------|
| `netlab version` returns an error | Install Netlab: [netlab.tools/install/ubuntu](https://netlab.tools/install/ubuntu/) |
| `netlab test clab` fails | Fix Netlab/Containerlab configuration before starting the server |
| Module import errors | Verify installation: `pip show neops-remote-lab` or `uv pip show neops-remote-lab` |

### "Another instance is running" / filelock error

A crashed or force-killed server may leave a stale lock. The server attempts automatic recovery on startup by checking whether the PID in the metadata file is still alive. If automatic recovery fails:

1. Confirm no server process is running: `pgrep -f neops-remote-lab`
2. Remove stale files: `rm /tmp/neops_remote_lab_server.lock /tmp/neops_remote_lab_server.meta.json`
3. Restart the server.

### "Address already in use" on port 8000

Another process is bound to the port. Find and stop it, or use a different port:

```bash
lsof -i :8000
# Kill the process, or:
neops-remote-lab --port 9000
```

### Netlab refuses to start a fresh topology

A stale `default` Netlab instance from a previous crash is blocking. The server clears this automatically at startup. If running Netlab manually, clean up first:

```bash
netlab down --cleanup
```

### Tests hang in queue

- Verify the server is reachable: `curl http://<host>:8000/healthz`
- Check that heartbeats are being sent (sessions without heartbeats are dropped after the stale timeout)
- Inspect server logs for session promotion messages

### Containers unreachable from test runner

- Verify VPN/Headscale connectivity to the lab subnets. See [Headscale VPN](../50-deployment/20-headscale-vpn.md) for setup instructions.
- Confirm `network_mode: host` in the topology if using host networking.
- Check firewall rules on the remote host.

### Lab stuck busy

If a client disconnected without releasing:

```bash
# Force-destroy with an active session
curl -s -X DELETE "http://localhost:8000/lab?force=true" \
     -H "X-Session-ID: $SESSION_ID"
```

The server's background cleanup will also eventually reclaim the lab after the active session's stale timeout expires (default 300 s).
