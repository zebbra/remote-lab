---
title: Debugging
description: The page to grep when something breaks — symptom/cause/fix table, common HTTP error codes, client and server log-pattern tables, the /debug/health endpoint, stale-state recovery.
tags: [reference, troubleshooting, server, client]
crosslink_defines: []
crosslink_references: []
---

# Debugging

Grep this page when something breaks — for any client, in any language. Symptom-first table below; underlying mechanisms and log patterns expand each row further down. For operator-side runbook entries (stuck filelocks, port conflicts, server startup), see [Administration → Troubleshooting](10-administration.md#troubleshooting).

!!! danger "No HTTP authentication"
    `neops-remote-lab` ships **without** bearer-token, OAuth, or mTLS
    authentication. The only access boundary on `/lab/*` is the
    `X-Session-ID` of an ACTIVE session. **Deploy behind a VPN.** See
    [Security model](30-security.md) for the full posture.

## Quick reference

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| `RuntimeError: REMOTE_LAB_URL not set` | The pytest fixture saw no `REMOTE_LAB_URL` in the environment | Export `REMOTE_LAB_URL` to point at your server. The fixture has no fallback to localhost — if you don't have a server, see [Local development server](../getting-started/20-local.md). |
| Tests hang in queue | Server unreachable, or another session holds the lab | Verify `curl $REMOTE_LAB_URL/healthz` returns 204. Check `GET /active-session` for the holder. See [Session queue → Promotion order](../10-concepts/20-session-queue.md#promotion-order). |
| `423 Locked` on every `/lab/*` call | Your session is `WAITING`, not `ACTIVE` | Poll `GET /session/{id}` until status is `active`. If it stays `waiting`, another session is ahead of you in the queue. |
| `423 Locked` on `POST /lab` only | Lab is busy with a different topology | The client retries every 5 s automatically. If you cannot wait, see "Lab stuck busy" below. |
| `404 Not Found` on `GET /session/{id}` | Session expired (heartbeat or queue timeout) | Create a new session. See [Stale-session eviction](../10-concepts/20-session-queue.md#stale-session-eviction) for the timeouts. |
| Lab stuck busy on every request | A previous session did not release | Force-destroy with `DELETE /lab?force=true` using an active `X-Session-ID`, or restart the server. See [Administration → Forced cleanup](10-administration.md#forced-cleanup-of-a-stuck-lab). |
| Containers unreachable from the test | VPN or routing problem | Confirm Tailscale/Headscale is up; check `network_mode: host` in the topology; review firewall rules. See [Headscale VPN](../40-deployment/20-headscale-quick-setup.md). |
| Connection refused on `$REMOTE_LAB_URL` | Server not running, wrong host, or VPN down | `curl $REMOTE_LAB_URL/healthz` should return 204. If it errors, fix transport before continuing. |

For the operator's view of the same symptom space (stale filelocks, port
conflicts, `netlab` not installed), see
[Administration → Troubleshooting](10-administration.md#troubleshooting).

---

## Debug logging

### Client-side

For pytest users, raise log verbosity to see fixture lifecycle events:

```bash
pytest -s --log-cli-level=DEBUG
```

This surfaces:

- Session creation and queue position.
- Session activation timing (`Session ... is active after Xs`).
- Topology upload and acquisition.
- HTTP status of `POST /lab/release` (204 No Content). On 2xx the
  client logs `Lab released successfully`; on exception it logs
  `Failed to release lab: <error>` and swallows the error so teardown
  continues. <!-- trace: neops_remote_lab/client.py:220 --> The server
  holds the reference counter, not the client.

For non-Python harnesses, the equivalent is whatever your HTTP client
library does — log every request URL, status code, and the
`X-Session-ID` you sent. The session and acquire flows have at most
six requests in the happy path; logging them is cheap and tells you
exactly which step failed.

### Server-side

Start the server with `--debug`:

```bash
neops-remote-lab --host 0.0.0.0 --port 8000 --debug
```

`--debug` does two things:

1. Sets log level to `DEBUG`, which surfaces session queue promotions,
   stale-session detection, and `LabManager` state transitions.
2. Enables `NEOPS_NETLAB_STREAM_OUTPUT=1`, which streams Netlab
   subprocess output (`netlab up`, `netlab down`, `netlab inspect`) to
   the server console in real time.

Without `--debug`, Netlab output is captured silently and only logged
on failure. Streaming is useful when `netlab up` is taking longer than
expected and you want to see what it's doing.

You can also enable streaming independently:

```bash
export NEOPS_NETLAB_STREAM_OUTPUT=1
neops-remote-lab --host 0.0.0.0 --port 8000 --log-level INFO
```

For all server flags and the logging configuration, see
[Configuration](20-configuration.md).

---

## The `/debug/health` endpoint

The server exposes a debug health endpoint with runtime statistics:

```bash
curl -s "$REMOTE_LAB_URL/debug/health" | jq .
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
| `uptime` | How long the server has been running. A low value after a crash signals a recent restart — your sessions from before the restart are gone. |
| `sessions` | Total tracked sessions. Compare with `queue_length` to see how many are waiting vs active. |
| `queue_length` | Sessions currently in the queue. If this is consistently high, you may need to lower CI concurrency or coordinate with the operator on `_WAITING_SESSION_TIMEOUT`. See [Session Queue → Queue contention](../10-concepts/20-session-queue.md#queue-contention-under-ci-load). |

The basic liveness check at `/healthz` returns `204` with no body — use
that for load balancer probes. `/debug/health` is for human consumption
and diagnostic scripts.

---

## Common HTTP error codes

When `RemoteLabClient` or your own code hits the REST API, these status
codes indicate specific conditions. The full status-code matrix per
endpoint is in [REST API](40-rest-api.md).

| Code | Endpoint(s) | Meaning | What to do |
|------|-------------|---------|------------|
| **400** | `POST /lab` | Bad request — topology file missing, or filename does not end in `.yml`/`.yaml` | Check the path you passed to `-F "topology=@..."` (or your client's equivalent) and that the file extension is correct. |
| **404** | `GET /session/{id}`, `POST /lab/release`, `DELETE /session/{id}` | Resource not found — session ID does not exist (likely expired), or (for `/lab/release`) no lab is currently held | Verify your `session_id`. If the session expired, create a new one. |
| **409** | `DELETE /lab?force=false` | Conflict — lab still has active references | Another session is using the lab. Use `force=true` if you really mean to evict, or wait for release. |
| **422** | `POST /lab`, `POST /lab/release`, `DELETE /lab`, `GET /lab/devices`, `POST /session/heartbeat` | Missing required `X-Session-ID` header | Send the `X-Session-ID` header on every `/lab/*` request and on heartbeat. |
| **423** | `POST /lab`, `GET /lab`, `POST /lab/release`, `DELETE /lab`, `GET /lab/devices` | Locked — your session is not `ACTIVE` (still waiting in the queue), or the lab is busy with a different topology | Wait for promotion (`GET /session/{id}` until `active`). If the lab is busy with another topology, the client retries every 5 s. |
| **502** | Any | Bad gateway — the server is behind a reverse proxy that cannot reach the backend | Check that the server process is running and the proxy configuration is correct. |

`DELETE /lab` returns `204 No Content` (not `404`) when the session is
`ACTIVE` but no lab is running — there is nothing to destroy. See
[REST API → `DELETE /lab`](40-rest-api.md#delete-lab-destroy-the-lab)
for the full matrix.

---

## Interpreting logs

Logs are emitted from two distinct processes — the client (or
`RemoteLabClient`, on the test runner) and the server (`remote-lab-server`
logger, on the lab host). Greps fail silently when you look for a
client-side string in server logs or vice versa, so split by owner.

### Client log patterns

Emitted by `neops_remote_lab.client` on the test runner. Visible with
`pytest --log-cli-level=INFO` or higher.

<!-- trace: neops_remote_lab/client.py:127 -->
<!-- trace: neops_remote_lab/client.py:170 -->
<!-- trace: neops_remote_lab/client.py:201 -->
<!-- trace: neops_remote_lab/client.py:220 -->
<!-- trace: neops_remote_lab/client.py:222 -->
<!-- trace: neops_remote_lab/client.py:243 -->

| Log pattern | What it means |
|-------------|---------------|
| `Session ... is active after X.Xs` | The client's `_wait_for_active_session` saw the session promote to `ACTIVE`. |
| `Session did not become active within Xs` | The client's `session_timeout` expired while the session was still `WAITING`; raised as `TimeoutError`. |
| `Lab acquired successfully.` | `acquire()` got 2xx from `POST /lab`. |
| `Lab released successfully` | `release()` got 2xx from `POST /lab/release`. |
| `Failed to release lab: <error>` | `release()` raised — suppressed during teardown so subsequent cleanup still runs. |
| `Closing session <sid>` / `Closed session <sid> successfully` | `close()` is sending / got 204/404 from `DELETE /session/{id}`. |

### Server log patterns

Emitted by the `remote-lab-server` logger on the lab host. Visible in
the server console (or `journalctl -u neops-remote-lab` if running under
`systemd`).

<!-- trace: neops_remote_lab/server.py:44 -->
<!-- trace: neops_remote_lab/server.py:210 -->
<!-- trace: neops_remote_lab/server.py:253 -->
<!-- trace: neops_remote_lab/server.py:260 -->
<!-- trace: neops_remote_lab/server.py:308 -->
<!-- trace: neops_remote_lab/netlab/lab_manager.py:252 -->
<!-- trace: neops_remote_lab/netlab/lab_manager.py:262 -->

| Log pattern | What it means |
|-------------|---------------|
| `Performing startup cleanup of stale netlab instances...` | Server lifespan is running `LabManager.cleanup(default_instance=True)`. |
| `Startup cleanup completed successfully` | Startup cleanup returned without raising (clean path). |
| `Startup cleanup encountered an error ...` | Startup cleanup raised — logged at WARNING; the server continues. Usually means no stale instance to clean. |
| `Created session <sid> at queue position N` | `POST /session` succeeded; `N=0` means immediately active, `N>0` means queued. |
| `Session <sid> promoted to ACTIVE (topology=...)` | `_promote_if_needed()` moved the session to the head of the queue. |
| `Removing stale session <sid> due to inactivity` | The cleanup loop dropped the session after `_WAITING_SESSION_TIMEOUT` (600 s) or `_ACTIVE_SESSION_STALE` (300 s) elapsed without activity. |
| `Cleaning up lab for stale active session <sid>` | Server is tearing down the lab of a session that just went stale. |
| `Tearing down lab <topo> (reason: <reason>)` | `LabManager._terminate_current` fired; reason is one of `server-startup`, `server-shutdown`, `stale-session-<sid>`, `client-end`, `manual-cleanup`. |
| `Lab <topo> became idle - awaiting next user or teardown (refcount=0)` | `release()` decremented ref to 0; the lab stays running until a different topology is requested or cleanup fires. See [Lab lifecycle → Release](../10-concepts/30-lab-lifecycle.md#release-the-refcount-decrements). |

When debugging a hanging test suite, find the latest `Created session`
in server logs and check whether `Session ... promoted to ACTIVE`
follows. If not, another session holds the lab — check which session is
at position 0 via `GET /active-session`.

---

## Stale-state recovery

If the server or a test run exits uncleanly, you may end up with
stale state. The server tries hard to clean up at startup and during
periodic background sweeps, but a few paths still need manual help.

**Server-side (operator runs):**

```bash
# Check whether a netlab instance is still running
netlab status

# Force-clean it
netlab down --cleanup
```

For stale lock files (`/tmp/neops_remote_lab_server.lock` or
`/tmp/netlab_pytest.lock`), follow the recovery procedure in
[Administration → Stale-lock recovery](10-administration.md#stale-lock-recovery)
— do not just delete them blindly. A stale lock is a signal that a
prior process crashed; investigate before clearing.

**Client-side:** there is rarely cleanup work to do. The server holds
all session and lab state; if your client crashes, the server's
stale-session cleanup will reclaim the slot after
`_ACTIVE_SESSION_STALE` (300 s) or `_WAITING_SESSION_TIMEOUT` (600 s).
If you cannot wait, end the orphaned session yourself:

```bash
# If you saved the session_id, you can DELETE without X-Session-ID
curl -s -X DELETE "$REMOTE_LAB_URL/session/<orphaned-session-id>"
```

---

## Where to go next

- **[REST API](40-rest-api.md)** — endpoint-by-endpoint reference. The
  authoritative source for status codes and response DTOs.
- **[Administration](10-administration.md)** — operator-side runbook
  (stale filelocks, port conflicts, `netlab` startup checks).
- **[Session queue](../10-concepts/20-session-queue.md)** — the FIFO
  state machine behind every queue-related symptom on this page.
- **[Lab lifecycle](../10-concepts/30-lab-lifecycle.md)** — what
  `try_acquire` does internally; the reuse and teardown rules behind
  `423 Locked` and `Lab ... became idle`.
- **[CI quickstart](../getting-started/40-ci.md)** — runner-pipeline shapes
  and the queue-tuning thread-out for the symptoms above when they recur
  under concurrency.
