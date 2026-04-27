---
title: Administration
description: Operator runbook for the Remote Lab Manager — starting the server, lock recovery, troubleshooting, and security posture.
tags: [how-to, operator, security]
crosslink_defines: []
crosslink_references: []
---

# Operator runbook

*Install, run under `systemd`, recover from a stale lock, unstick a wedged lab. The day-1 and day-N operator handbook for a shared host.*

=== "uv (recommended)"

    ```bash
    uv tool install neops-remote-lab
    ```

    [`uv tool install`](https://docs.astral.sh/uv/concepts/tools/) drops
    the CLI in `~/.local/bin` (or `uv tool dir`) inside an isolated
    environment that uv manages.

=== "pipx"

    ```bash
    pipx install neops-remote-lab
    pipx ensurepath  # only needed once
    ```

    [pipx](https://pipx.pypa.io/) installs into a per-app virtualenv
    under `~/.local/pipx/venvs/`. After the first install, run
    `pipx ensurepath` and re-login so `~/.local/bin` is on `PATH`.

=== "pip (last resort)"

    ```bash
    python -m venv ~/.venvs/neops-remote-lab
    ~/.venvs/neops-remote-lab/bin/pip install neops-remote-lab
    ln -s ~/.venvs/neops-remote-lab/bin/neops-remote-lab ~/.local/bin/
    ```

    Manual virtualenv plus a symlink. Prefer `uv tool install` or `pipx`
    unless you have a hard reason not to.

Verify the CLI is reachable and can print its help:

```bash
which neops-remote-lab
neops-remote-lab --help
```

The help output lists the complete server CLI surface: `--debug`,
`--host`, `--port`, `--log-level`, `--log-config`, and `--version`. <!-- trace: neops_remote_lab/__main__.py:149 -->
If `neops-remote-lab --help` errors with `command not found`, your
tool's `bin` directory is not on `PATH` — run `uv tool update-shell`,
`pipx ensurepath`, or add the symlink target manually depending on which
installer you used.

!!! danger "No HTTP authentication"
    `neops-remote-lab` ships **without** bearer-token, OAuth, or mTLS
    authentication. The only access boundary on `/lab/*` is the
    `X-Session-ID` of an ACTIVE session. **Deploy behind a VPN.** See
    [Security model](30-security.md) for the full posture.

!!! info "Before you start"
    Netlab CLI must already be on `PATH` — the launcher refuses to start without it. <!-- trace: neops_remote_lab/__main__.py:206 --> If the host is fresh, run [Netlab host setup](../40-deployment/10-netlab-host-setup.md) first. You'll also want shell access with permission to read `/tmp`, kill processes, and restart the service.

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
--8<-- "examples/systemd/neops-remote-lab.service"
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

See [Configuration → Server CLI flags](20-configuration.md#server-cli-flags) for
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
see the note in the [REST API reference](40-rest-api.md).

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

```bash title="examples/scripts/force_cleanup.sh"
--8<-- "examples/scripts/force_cleanup.sh"
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

!!! info "Looking for client-side debugging or HTTP error codes?"
    This troubleshooting table is for operators of the lab host. For
    client-side debugging, log patterns, and the HTTP-error-code
    reference, see [Debugging](50-debugging.md).

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

- [REST API](40-rest-api.md) — endpoint reference for operator scripting
- [Configuration](20-configuration.md) — flags and environment variables
- [Security model](30-security.md) — the threat model the operational guidance above is built on top of
- [Architecture](../10-concepts/10-architecture.md) — where the single-instance + one-lab invariants come from
- [Session Queue](../10-concepts/20-session-queue.md) — FIFO semantics and 423 Locked flow
- [Headscale VPN — Quick setup](../40-deployment/20-headscale-quick-setup.md) — the recommended VPN enclosure
