---
page_purpose: troubleshooting
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# Debugging and Troubleshooting

## Quick Reference

| Symptom | Likely cause | Fix |
|---------|-------------|-----|
| Server won't start | Netlab not installed or not in `PATH` | Run `netlab version` and `netlab test clab`. Install Netlab if missing. |
| `filelock` error / "another instance is running" | Crashed process left a stale lock or another server is running | Check for live `neops-remote-lab` processes. If none exist, remove the lock file in the system temp directory (e.g., `/tmp/neops_remote_lab_server.lock`). |
| `Address already in use` on port 8000 | Another process is bound to the port | `lsof -i :8000` to find it. Kill or use a different `--port`. |
| Netlab refuses to start a fresh topology | Stale `default` netlab instance from a crashed prior run | The server clears this at startup automatically. If running netlab by hand, run `netlab down --cleanup` first. |
| Tests hang in queue | Server unreachable, or another session holds the lock | Verify port 8000 is reachable. Check server logs for the active session. |
| Containers unreachable from tests | Network routing issue | Confirm VPN/Headscale is up. Check `network_mode: host` in the topology. Review firewall rules. |
| Lab stuck busy (423 on every request) | Previous session did not release | Force-destroy with `DELETE /lab?force=true` using an active `X-Session-ID`, or restart the server. |
| `RuntimeError: REMOTE_LAB_URL not set` | `remote_lab_fixture` always requires a Remote Lab Manager server | Export `REMOTE_LAB_URL` to point at your server. The fixture does not fall back to local execution; if you have no server, see [Local Lab Testing](20-local-testing.md) for the direct `LabManager` pattern. |

## Debug Logging

### Client-side

Increase pytest log verbosity to see fixture lifecycle events:

```bash
pytest -s --log-cli-level=DEBUG
```

This surfaces:

- Fixture mode detection (local vs. remote)
- Session creation and queue position
- Topology upload and acquisition timing
<!-- trace: neops_remote_lab/client.py:127 -->
- HTTP status of `POST /lab/release` (204 No Content). On 2xx the client logs `Lab released successfully`; on exception it logs `Failed to release lab: <error>` and swallows the error so teardown continues (`client.py:213-222`). No response body is read or logged -- the server holds the reference counter.

### Server-side

Start the server with the `--debug` flag:

```bash
neops-remote-lab --host 0.0.0.0 --port 8000 --debug
```

`--debug` does two things:

1. Sets log level to `DEBUG`, which includes session queue promotions, stale session detection, and `LabManager` state transitions
2. Enables `NEOPS_NETLAB_STREAM_OUTPUT=1`, which streams Netlab subprocess output (`netlab up`, `netlab down`, `netlab inspect`) to the server console in real time

Without `--debug`, Netlab output is captured silently and only logged on failure. Streaming is useful when you need to see what Netlab is doing during a long `netlab up`.

You can also enable streaming independently:

```bash
export NEOPS_NETLAB_STREAM_OUTPUT=1
neops-remote-lab --host 0.0.0.0 --port 8000 --log-level INFO
```

See [Configuration](../20-server/20-configuration.md) for all server flags and the logging configuration file format.

## The /debug/health Endpoint

The server exposes a debug health endpoint with runtime statistics:

```bash
curl -s http://<host>:8000/debug/health | jq .
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

| Field | What it tells you |
|-------|-------------------|
| `uptime` | How long the server has been running. A low value after a crash suggests the server restarted recently. |
| `sessions` | Total tracked sessions. Compare with `queue_length` to see how many are waiting vs. active. |
| `queue_length` | Sessions in the queue. If this is consistently high, you may need a longer `REMOTE_LAB_SESSION_TIMEOUT` on clients or more capacity. |

The basic liveness check at `/healthz` returns `204` with no body -- use it for load balancer probes. `/debug/health` is for human consumption and development diagnostics.

## Common HTTP Error Codes

When `RemoteLabClient` or your own code hits the REST API, these status codes indicate specific conditions:

| Code | Endpoint(s) | Meaning | What to do |
|------|-------------|---------|------------|
| **400** | `POST /lab` | Bad request -- topology file missing a filename, or not a `.yml`/`.yaml` file | Check that the topology path exists and has the right extension |
| **404** | `GET /session/{id}`, `POST /lab/release`, `DELETE /session/{id}` | Resource not found -- session ID does not exist, or (for `/lab/release`) no lab is running | Verify your `session_id` is correct. If the session expired, create a new one. |
| **409** | `DELETE /lab?force=false` | Conflict -- lab still has active references | Another test or session is using the lab. Use `force=true` or wait for release. |
| **423** | `POST /lab`, `GET /lab`, `POST /lab/release` | Locked -- session is not `ACTIVE` (still waiting in queue), or lab is busy with another topology | Wait for your session to become active. If the lab is busy, the client retries automatically every 5 seconds. |
| **502** | Any | Bad gateway -- the server is behind a reverse proxy that cannot reach the backend | Check that the server process is running and the proxy configuration is correct |

`DELETE /lab` returns `204 No Content` (not `404`) when the session is `ACTIVE` but no lab is running -- there is nothing to destroy. See the [REST API reference](../20-server/10-rest-api.md#delete-lab) for the full status-code matrix.

See [REST API](../20-server/10-rest-api.md) for complete endpoint documentation.

## Interpreting Logs

Logs are emitted from two distinct processes -- the pytest client (`RemoteLabClient`) and the server (`remote-lab-server` logger) -- and greps fail silently when you look for a client-side string in server logs or vice versa. Split by owner.

### Client log patterns

<!-- trace: neops_remote_lab/client.py:127-131 -->
Emitted by `neops_remote_lab.client` on the test runner. Visible with `pytest --log-cli-level=INFO` or higher.

<!-- trace: neops_remote_lab/client.py:220 -->
| Log pattern | What it means | Source |
|-------------|---------------|--------|
| `Session ... is active after X.Xs` | `_wait_for_active_session` observed the session become `ACTIVE`. | `client.py:127-131` |
| `Session did not become active within Xs` | The client's `session_timeout` expired while the session was still `WAITING` (the message text is raised as `TimeoutError`). | `client.py:170` |
| `Lab released successfully` | `release()` got a 2xx from `POST /lab/release`. | `client.py:220` |
| `Failed to release lab: <error>` | `release()` raised -- suppressed during teardown. | `client.py:222` |
| `Lab acquired successfully.` | `acquire()` received a 2xx from `POST /lab`. | `client.py:201` |
| `Closing session <sid>` / `Closed session <sid> successfully` | `close()` is sending / got 204/404 from `DELETE /session/{id}`. | `client.py:243,252` |

### Server log patterns

<!-- trace: neops_remote_lab/server.py:253 -->
<!-- trace: neops_remote_lab/server.py:261 -->
Emitted by the `remote-lab-server` logger. Visible in the server's console (or journal via systemd).

| Log pattern | What it means | Source |
|-------------|---------------|--------|
| `Performing startup cleanup of stale netlab instances...` | Server lifespan is running `LabManager.cleanup(default_instance=True)`. | `server.py:44` |
| `Startup cleanup completed successfully` | Startup cleanup returned without raising (INFO-level, clean path). | `server.py:47` |
| `Startup cleanup encountered an error ...` | Startup cleanup raised -- logged at WARNING; server continues. | `server.py:49` |
| `Created session <sid> at queue position N` | `POST /session` succeeded; N=0 means immediately active, N>0 means queued. | `server.py:308` |
| `Session <sid> promoted to ACTIVE (topology=...)` | `_promote_if_needed()` moved the session to the head of the queue. | `server.py:210` |
| `Removing stale session <sid> due to inactivity` | Cleanup task dropped the session after `_WAITING_SESSION_TIMEOUT` or `_ACTIVE_SESSION_STALE` elapsed without a heartbeat. | `server.py:253` |
| `Cleaning up lab for stale active session <sid>` | Server is tearing down the lab of a session that just went stale; the cleanup reason passed into `LabManager.cleanup()` is `stale-session-<sid>`. | `server.py:260-261` |
| `Tearing down lab <topo> (reason: <reason>)` | `LabManager._terminate_current` fired; reason is one of `server-startup`, `server-shutdown`, `stale-session-<sid>`, `client-end`, `manual-cleanup`. | `lab_manager.py:262` |
| `Lab <topo> became idle - awaiting next user or teardown (refcount=0)` | `release()` decremented ref to 0; lab stays running until a different topology is requested or cleanup fires. | `lab_manager.py:252` |

When debugging a hanging test suite, find the latest `Created session` in server logs and check whether `Session ... promoted to ACTIVE` follows. If not, another session holds the lab -- check which session is at position 0 via `GET /active-session`.

## Stale State Recovery

If the server or a test run exits uncleanly, you may end up with stale state:

**Server side:**

```bash
# Check if a netlab instance is still running
netlab status

# Clean it up
netlab down --cleanup

# If the server lock file is stale
rm /tmp/neops_remote_lab_server.lock
rm /tmp/neops_remote_lab_server.meta.json
```

**Client side (local mode):**

```bash
# Remove the cross-process lock if a pytest worker crashed
rm /tmp/netlab_pytest.lock
```

The server performs automatic cleanup of stale sessions and Netlab instances at startup and during periodic background sweeps. See [Lab Lifecycle -- Cleanup](../10-concepts/30-lab-lifecycle.md#cleanup) and [Administration](../20-server/30-administration.md) for details.
