---
title: Session Queue
description: FIFO session model — how WAITING sessions are promoted to ACTIVE, how heartbeats keep them alive, and when the server evicts them.
tags: [concept, server, lifecycle, testing]
crosslink_defines: []
crosslink_references: []
---

# Session Queue

Only one lab runs per host, so only one client can drive it at a time. The
session queue is the mechanism that decides who goes next, and it is the only
thing standing between well-behaved cooperation and a deadlocked test suite.

> **Why a queue and not a mutex?** Netlab topologies take minutes to bring up.
> Holding a kernel mutex for that long would block every health check and
> status poll. The queue lets clients poll their own status at whatever cadence
> they choose while only one client at a time drives Netlab.

## The state machine

Every session is in exactly one of two states:

```mermaid
stateDiagram-v2
    [*] --> WAITING: POST /session
    WAITING --> ACTIVE: queue head & previous active released
    ACTIVE --> [*]: DELETE /session/{id}
    WAITING --> [*]: 600s without movement
    ACTIVE --> [*]: 300s without heartbeat
```

The queue itself is a plain Python list in the server process; the head is the
ACTIVE session (if any), and the rest are WAITING in insertion order.

## Creating a session

<!-- trace: neops_remote_lab/server.py:292 -->
`POST /session` generates a UUID, appends it to the queue, and immediately
invokes the promotion helper. If the queue was empty the new session is
promoted to ACTIVE before the response returns; otherwise it stays WAITING at
position `len(queue) - 1`.

```bash
curl -s -X POST http://$LAB_HOST:8000/session
```

```json
{"session_id":"c3f1a9e2-...-b7","position":0}
```

Position 0 means ACTIVE. Any higher number is the number of sessions ahead of
you in line.

## Promotion is strict FIFO

<!-- trace: neops_remote_lab/server.py:185 -->
`_promote_if_needed` walks the queue head and promotes only the first WAITING
session. The queue order is never rearranged: if a client three places back
gets impatient and `DELETE`s its session, that slot is removed without
affecting anyone else's position.

> **Why strict FIFO?** Any priority scheme needs a reason to prefer one test
> over another. None of the consumer projects — most importantly
> `neops-worker-sdk-py` — surface that intent to the server, so the server
> doesn't try to guess. First-come, first-served is the only fair default.

## The access boundary

<!-- trace: neops_remote_lab/server.py:390 -->
Every `/lab/*` endpoint is gated by a dependency that looks up the
`X-Session-ID` header, confirms the session exists, and checks that its
status is `ACTIVE`. A missing header fails schema validation (422); an
unknown session returns 404; a known but WAITING session returns
`423 Locked`.

<!-- trace: neops_remote_lab/server.py:482 -->
`/session/heartbeat` does **not** share that dependency. It is declared
with a plain `Header(...)` parameter and only checks that the session
exists (404 if unknown), which is why a client can heartbeat while still
WAITING in the queue. See [The heartbeat](#the-heartbeat) below for why
that matters.

!!! danger "423 Locked is the only auth"
    This is the sole access boundary on the lab surface. There is no Bearer
    token, no mTLS, no tenant header. Run the server behind a VPN or on a
    trusted internal network — treat an exposed port as equivalent to giving
    the internet root access to your lab host.

## The heartbeat

An ACTIVE session must prove it is still alive. The fixture and
`RemoteLabClient` do this automatically; any other caller has to do it by
hand.

<!-- trace: neops_remote_lab/server.py:481 -->
`POST /session/heartbeat` with `X-Session-ID: <id>` updates the session's
`last_seen_at` timestamp and returns 204. It works for both WAITING and ACTIVE
sessions (the state gate is only on `/lab/*`).

```bash
curl -X POST http://$LAB_HOST:8000/session/heartbeat \
     -H "X-Session-ID: $SESSION"
```

```
HTTP/1.1 204 No Content
```

??? info "What counts as a heartbeat?"
    Calls to `GET /session/{id}`, `GET /active-session`, `GET /lab`,
    `GET /lab/devices`, `POST /lab`, `POST /lab/release`, and
    `DELETE /lab` all update `last_seen_at` on their way through. In
    practice any real activity keeps the session alive; the dedicated
    heartbeat endpoint is the cheapest option for long-running tests that
    aren't touching the lab API.

## Stale-session eviction

A crashed client cannot unregister itself. The server has two timeouts to keep
the queue from deadlocking.

<!-- trace: neops_remote_lab/server.py:95 -->
A WAITING session is dropped after 600 seconds of no activity. An ACTIVE
session is deemed stale after 300 seconds without a heartbeat.

| State | Timeout | Why this value |
|---|---|---|
| WAITING | 600s | `netlab up` can take minutes; a slow queue ahead is not a client bug. |
| ACTIVE | 300s | Short enough that a crashed test releases the lab promptly; long enough that normal test setup doesn't trigger it. |

<!-- trace: neops_remote_lab/server.py:259 -->
When an ACTIVE session is evicted, the server runs `LabManager.cleanup` to
tear down the lab, then promotes the next WAITING session to ACTIVE. The
incoming test will see a fresh lab — not the evicted session's.

## The cleanup loop cadence

<!-- trace: neops_remote_lab/server.py:275 -->
The background cleanup task is adaptive: it runs every 5 seconds when the
queue has multiple sessions, every 15 seconds when exactly one ACTIVE session
is present, and every 30 seconds when the queue is empty. This keeps stale
sweeps responsive under contention without burning CPU on an idle host.

## Ending a session cleanly

`DELETE /session/{id}` removes the session from the queue and, if it was
ACTIVE, triggers `LabManager.cleanup` and promotes the next session. No
`X-Session-ID` header is required — anyone with the session ID can end it.

```bash
curl -X DELETE http://$LAB_HOST:8000/session/$SESSION
```

```
HTTP/1.1 204 No Content
```

## Polling from a client's perspective

```bash
SESSION=$(curl -s -X POST http://$LAB_HOST:8000/session | jq -r .session_id)

while true; do
    STATUS=$(curl -s "http://$LAB_HOST:8000/session/$SESSION" | jq -r .status)
    [[ $STATUS == "active" ]] && break
    sleep 5
done
```

Expected sequence during a busy queue:

```
{"status":"waiting","position":2}
{"status":"waiting","position":1}
{"status":"active","position":0}
```

`RemoteLabClient` does this automatically with exponential backoff on
retriable errors. See [remote-lab-client.md](../client/20-python-client.md) when it
lands.

## Common pitfalls

!!! warning "Don't send heartbeats faster than every few seconds"
    The heartbeat is cheap but not free. Polling aggressively in a tight loop
    can mask a real bug (your test never actually invoked the lab endpoints)
    and floods the server logs. The fixture sends on a sensible schedule; if
    you're writing a custom client, aim for every 60-120 seconds.

!!! warning "Don't assume position is stable"
    Your reported `position` can jump around if sessions ahead of you get
    evicted or cancelled. Only `status == "active"` is a guarantee you can
    drive the lab.

## Where to go next

- [lab-lifecycle.md](30-lab-lifecycle.md) — what happens after promotion:
  uploading a topology, reuse semantics, and release.
- [architecture.md](10-architecture.md) — how this queue sits inside the broader
  server + client topology.
