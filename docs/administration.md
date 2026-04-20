---
title: Administration
description: Operator runbook for the Remote Lab Manager — starting the server, lock recovery, troubleshooting, and security posture.
tags: [how-to, operator, security]
crosslink_defines: []
crosslink_references: []
---

# Administration

Operator runbook for keeping the Remote Lab Manager healthy on a shared host.
Read the [Security posture](#security-posture) section before exposing the
server on any network you do not fully control.

!!! info "Prerequisites"
    - Familiarity with the [architecture](architecture.md) and [REST API](rest-api.md).
    - Shell access to the lab host with permission to read `/tmp`, kill processes, and restart the `neops-remote-lab` service.
    - `netlab` CLI installed and on `PATH`. If it is missing, the server exits before binding the port. <!-- trace: neops_remote_lab/__main__.py:206 -->

---

## Installing the server

!!! note "Netlab host setup comes first"
    This section assumes the Netlab CLI is already installed and runnable
    on the lab host. If you are starting from a fresh VM, complete
    [Netlab host setup](netlab_configuration.md) first — the server
    launcher will refuse to start without `netlab` on `PATH`. <!-- trace: neops_remote_lab/__main__.py:206 -->

The server ships as the `neops-remote-lab` Python distribution. The
recommended install is [pipx](https://pipx.pypa.io/) so the CLI lands on
`PATH` in its own virtualenv without polluting the system Python:

```bash
# Requires Python 3.12+
pipx install neops-remote-lab
```

The distribution declares a `neops-remote-lab` console script that points
at `neops_remote_lab.__main__:main`, so `pipx install` puts the server
CLI directly on `PATH`. <!-- trace: pyproject.toml:34 -->

Verify the CLI is reachable and can print its help:

```bash
which neops-remote-lab
neops-remote-lab --help
```

The help output lists the complete server CLI surface: `--debug`,
`--host`, `--port`, `--log-level`, `--log-config`, and `--version`. <!-- trace: neops_remote_lab/__main__.py:149 -->
If `neops-remote-lab --help` errors with `command not found`, run
`pipx ensurepath` and re-login, or place `<INSTALL_PATH>/bin` on `PATH`
manually (replace `<INSTALL_PATH>` with the pipx venv path —
`pipx environment --value PIPX_LOCAL_VENVS` gives the default).

Once the CLI is reachable, continue with [Starting the server](#starting-the-server)
for a one-shot foreground run, or [Running as a system service](#running-as-a-system-service)
to put the server under `systemd`.

---

## Running as a system service

The server is a long-running process that needs to come back after a
reboot. The recommended supervisor on Linux hosts is `systemd`. A minimal
unit file looks like this — save it at
`/etc/systemd/system/neops-remote-lab.service`:

```ini title="/etc/systemd/system/neops-remote-lab.service"
[Unit]
Description=neops-remote-lab Manager
After=network-online.target docker.service
Wants=network-online.target

[Service]
Type=simple
User=<SERVICE_USER>
Group=<SERVICE_USER>
# <INSTALL_PATH> is the pipx venv or virtualenv where neops-remote-lab was installed.
# With the default pipx layout, that is typically /home/<SERVICE_USER>/.local/pipx/venvs/neops-remote-lab.
ExecStart=<INSTALL_PATH>/bin/neops-remote-lab --host 0.0.0.0 --port 8000 --log-level INFO
Restart=on-failure
RestartSec=5
# Logs land in the journal by default (stdout/stderr). Override with --log-config to redirect.
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

Install, enable, and start it:

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now neops-remote-lab
```

Verify the service is up and watch its logs:

```bash
systemctl status neops-remote-lab
journalctl -u neops-remote-lab -f
```

`journalctl -u neops-remote-lab -f` follows the server's structured log
stream in the journal; send it to `<LOG_PATH>` via `--log-config` if you
need a file-based handler instead.

!!! warning "One systemd unit per host only"
    The server acquires a cross-process `FileLock` at startup and exits
    with status 1 if another instance already holds it. <!-- trace: neops_remote_lab/__main__.py:104 -->
    Do **not** define a second `neops-remote-lab@.service` template
    instance on the same host — the second unit will crashloop on the
    lock, fill the journal, and `systemctl status` will flap. The
    one-server-per-host invariant is a hard constraint, not a tunable.

---

## Starting the server

The entry point is:

```bash
neops-remote-lab --host 0.0.0.0 --port 8000 --log-level INFO
```

See [Configuration → Server CLI flags](configuration.md#server-cli-flags) for
every supported flag.

On startup the server, in order:

1. Sets up logging.
2. Acquires a global single-instance `FileLock` (see below).
3. Writes an instance-metadata JSON file.
4. Verifies the `netlab` CLI is reachable.
5. Starts Uvicorn.
6. Dispatches a one-shot best-effort cleanup of any stale Netlab `default`
   instance left over from a crashed prior run. <!-- trace: neops_remote_lab/server.py:46 -->

### Single-instance filelock

Only one Remote Lab Manager may run per host. The entry point acquires a
`FileLock` at a fixed path under the system temp directory, or exits if
another instance already holds it. <!-- trace: neops_remote_lab/__main__.py:104 -->

The paths, on a typical Linux host:

| File | Purpose |
|---|---|
| `/tmp/neops_remote_lab_server.lock` | The filelock itself |
| `/tmp/neops_remote_lab_server.meta.json` | Human-readable metadata about the running instance |

On successful startup the server writes the metadata JSON. <!-- trace: neops_remote_lab/__main__.py:186 --> Fields:

| Field | Value |
|---|---|
| `pid` | Process id of the running server |
| `user` | Unix user the process is running as |
| `host` | `platform.node()` of the lab host |
| `started_at` | Unix timestamp |
| `port` | Value of `--port` |
| `host_bind` | Value of `--host` |
| `log_level` | Effective log level |
| `log_config` | Path to the logging config in use |
| `version` | Package version |
| `cwd` | Working directory at launch |
| `cmd` | Full `argv` used to launch the process |

Inspect it directly when you need to know *who* is running the server:

```bash
jq . /tmp/neops_remote_lab_server.meta.json
```

On normal exit the server deletes the metadata file and releases the lock via
a `finally`-guarded `_cleanup_lock()` callback. <!-- trace: neops_remote_lab/__main__.py:174 -->

### Stale-lock recovery

The most common failure after a crash is a stale lockfile. The startup path
handles this automatically:

1. Attempt `lock.acquire(timeout=0)` — fails if the lock is held.
2. Read `meta.json`.
3. If the recorded `pid` is not alive, remove the stale `meta.json` and retry
   the lock. <!-- trace: neops_remote_lab/__main__.py:114 -->
4. If the recorded `pid` is alive, log the full running-instance details
   (pid/user/host/version/bind/started) and exit with status 1.

**Manual recovery** is rarely needed, but the procedure is:

```bash
# Inspect the claimed owner
jq . /tmp/neops_remote_lab_server.meta.json

# Confirm it is really gone
ps -p "$(jq .pid /tmp/neops_remote_lab_server.meta.json)" || echo "not running"

# Remove both files and restart
rm -f /tmp/neops_remote_lab_server.lock /tmp/neops_remote_lab_server.meta.json
neops-remote-lab --host 0.0.0.0 --port 8000
```

!!! warning "Do not remove the lockfile while another instance is running"
    Two simultaneous instances cannot be guaranteed safe — the Netlab
    `default` instance is a single cross-process resource. If two servers both
    think they own it, lab state will be destroyed out from under active
    sessions.

---

## Security posture

!!! danger "The service has no authentication — treat it as internal-trust"
    The `REMOTE_LAB_TOKEN` / Bearer-auth path in `RemoteLabClient` is
    **commented out** and no endpoint in `server.py` enforces bearer
    authentication. <!-- trace: neops_remote_lab/client.py:46 -->

### The only access boundary

The sole boundary on `/lab/*` and `/session/heartbeat` is the `X-Session-ID`
header — and only for a session that is currently in the ACTIVE state in the
FIFO queue. <!-- trace: neops_remote_lab/server.py:390 -->

- Unknown session ids → `404 Not Found`
- Waiting (not-yet-ACTIVE) session ids → `423 Locked`
- Anyone who can create a session (`POST /session`, no auth) can eventually
  reach ACTIVE by waiting in the queue.

This is explicitly called out as an invariant in [`AGENTS.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/AGENTS.md).
The service is designed for **internal** CI networks, not for the public
internet.

### Operational guidance

| Do | Don't |
|---|---|
| Bind the server behind a VPN (Headscale, WireGuard, Tailscale). | Expose `:8000` to the public internet. |
| Use `--host` to bind to a specific interface when the host has a public NIC. | Leave `--host 0.0.0.0` on a multi-homed host without a firewall. |
| Restrict network reachability with host/cloud firewall rules. | Rely on `X-Session-ID` as a secret — it's returned by an unauthenticated `POST /session`. |
| Use a reverse proxy (nginx, Caddy) with TLS + mutual auth if you must expose across hosts. | Assume HTTPS by itself protects the endpoints — the service still trusts any caller able to complete the session handshake. |

### When you expose the service

If your deployment requires network reachability beyond a single VPN, layer
these controls in front of the server:

1. **Network-level ACLs** — restrict TCP 8000 to known caller subnets.
2. **mTLS at a reverse proxy** — each caller presents a client certificate.
3. **Rate limiting** on `POST /session` — prevents queue-flooding.

None of this replaces the need to treat the service as internal; it reduces
the blast radius of a compromised caller.

---

## Routine operations

### Checking server health

```bash
curl -fsS "http://$LAB_HOST:8000/healthz"
# Exit code 0 = alive
```

For richer stats during an incident:

```bash
curl -s "http://$LAB_HOST:8000/debug/health" | jq .
```

Returns uptime, queue length, and session count. Intended for debugging only —
see the note in the [REST API reference](rest-api.md#endpoints-not-documented-here).

### Log monitoring

The server emits structured logs with the session id prefix:

```text
2026-04-20 12:34:56 | INFO     | remote-lab-server | sid=24f1a2e0 topo=simple_frr.yml | Created session
```

Keys to watch:

| Log event | Meaning |
|---|---|
| `Session <id> promoted to ACTIVE` | A waiting session moved to the head of the queue |
| `Removing stale session <id> due to inactivity` | Heartbeat missed the 300 s window; lab will be cleaned up |
| `Lab currently busy` at level WARN | `POST /lab` returned 423 because a different topology is already running |
| `netlab ... failed with exit code ...` at level ERROR | Topology failed to come up; see the captured Netlab output |

### Forced cleanup of a stuck lab

If a lab is stuck (`netlab up` failed partway through, or a client crashed
without releasing), take the lab down via the REST API using any ACTIVE
session:

```bash
SESSION_ID=$(curl -s -X POST "http://$LAB_HOST:8000/session" | jq -r .session_id)

# Wait for ACTIVE
while [[ "$(curl -s "http://$LAB_HOST:8000/session/$SESSION_ID" | jq -r .status)" != "active" ]]; do
  sleep 2
done

# Force destroy
curl -s -X DELETE "http://$LAB_HOST:8000/lab?force=true" \
  -H "X-Session-ID: $SESSION_ID"

curl -s -X DELETE "http://$LAB_HOST:8000/session/$SESSION_ID"
```

As a last resort (server unreachable or wedged), clean up Netlab directly on
the host:

```bash
netlab down --cleanup --instance default
```

Remember: **only one operator should be doing this at a time**. The Netlab
`default` instance is the single cross-process resource.

---

## Troubleshooting

| Symptom | Likely cause | Recovery |
|---|---|---|
| `Another Remote Lab Manager instance is already running.` on startup | Filelock held by another (possibly dead) process | Inspect `/tmp/neops_remote_lab_server.meta.json`; if PID is not alive, delete the lock + meta file and retry. See [Stale-lock recovery](#stale-lock-recovery). |
| `'netlab' CLI not found in PATH.` at startup, exit 1 | Netlab not installed or not on the launcher's `PATH` | Install Netlab; verify with `netlab version`; retry. <!-- trace: neops_remote_lab/__main__.py:206 --> |
| `Address already in use` on the configured port | Prior server did not exit cleanly, or another service occupies the port | `lsof -i :8000`; kill the process or start with `--port`. |
| All `POST /lab` calls return 423 Locked from one caller | The caller's session is not ACTIVE, or a different topology owns the host | Check `GET /session/{id}`; if WAITING, wait; if ACTIVE, another topology is running — release or force-destroy. |
| Clients time out in `_wait_for_active_session` | Session is still in the queue after 600 s | The server is clearing waiting sessions every 600 s; check server logs for queue state and `Lab currently busy` messages. |
| Session silently disappears mid-test | Heartbeat missed the 300 s window | Ensure the fixture is session-scoped; check client logs for heartbeat failures; consider raising `REMOTE_LAB_REQUEST_TIMEOUT`. |
| `netlab down` hangs when removing a topology manually | Containers wedged in an error state | `docker ps` / `containerlab destroy --all`; restart Docker as a last resort. |
| Zombie metadata after `kill -9` | The `finally` block did not run | Remove `/tmp/neops_remote_lab_server.meta.json` manually after confirming no server is running. |

---

## See also

- [REST API](rest-api.md) — endpoint reference for operator scripting
- [Configuration](configuration.md) — flags and environment variables
- [Architecture](architecture.md) — where the single-instance + one-lab invariants come from
- [Session queue](session-queue.md) — FIFO semantics and 423 Locked flow
- [Headscale + Tailscale VPN setup](headscale_headplane.md) — common deployment model for private reachability
