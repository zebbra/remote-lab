---
title: REST API Reference
description: Endpoint-by-endpoint reference for the Remote Lab Manager HTTP surface — sessions, lab acquisition, release, devices.
tags: [reference, api, server]
crosslink_defines: []
crosslink_references: []
---

# REST API Reference

Every endpoint the Remote Lab Manager exposes for direct consumer use, with **schema**, **error codes**, and an **example invocation**. The contract table below is the load-bearing part — `X-Session-ID` is the only access boundary on `/lab/*`.

!!! danger "No HTTP authentication"
    `neops-remote-lab` ships **without** bearer-token, OAuth, or mTLS
    authentication. The only access boundary on `/lab/*` is the
    `X-Session-ID` of an ACTIVE session. **Deploy behind a VPN.** See
    [Security model](30-security.md) for the full posture.

## The X-Session-ID contract

| Endpoint pattern | Header required | Non-active session response |
|---|---|---|
| `POST /session` | no | — |
| `GET /session/{id}` | no | — |
| `DELETE /session/{id}` | no | — |
| `POST /session/heartbeat` | **yes** | 404 if session missing |
| `POST /lab` | **yes** | 423 Locked if session not ACTIVE |
| `POST /lab/release` | **yes** | 423 Locked if session not ACTIVE |
| `DELETE /lab` | **yes** | 423 Locked if session not ACTIVE |
| `GET /lab/devices` | **yes** | 423 Locked if session not ACTIVE |

The server enforces the active-session check via a `_get_active_session` FastAPI dependency: unknown session ids raise 404, non-active sessions raise 423 Locked. <!-- trace: neops_remote_lab/server.py:381 -->

---

## Sessions

### `POST /session` — create a session

Creates a new session, appends it to the FIFO queue, and returns its id and
initial queue position. <!-- trace: neops_remote_lab/server.py:292 -->

If the queue was empty the new session is promoted to `ACTIVE` before the
response is returned, so single-client callers see `position: 0` immediately.

**Request** — no body, no headers required.

**Response** — `201 Created`, `CreateSessionResponseDto`:

| Field | Type | Description |
|---|---|---|
| `session_id` | string (uuid4) | Opaque identifier — send on every subsequent `/lab/*` and `/session/heartbeat` request |
| `position` | integer | 0 if immediately promoted to ACTIVE, else position in the queue at creation time |

=== "cURL"

    ```bash
    curl -s -X POST "$BASE_URL/session"
    ```

=== "Expected output"

    ```json
    {"session_id": "f8e7c1b2-...-...", "position": 0}
    ```

??? info "Conventions used below"
    All cURL examples assume `$BASE_URL` is exported (e.g. `export BASE_URL="http://lab.internal:8000"`).

    - **Content types** — JSON bodies are `application/json`; `POST /lab` is the only `multipart/form-data` endpoint.
    - **DTO suffix** — Pydantic 2 request/response models in the source are suffixed `*Dto` (e.g., `CreateSessionResponseDto`). Field order below matches the source models. See [Invariants → `*Dto` suffix](../50-contributing/20-invariants.md#dto-suffix).
    - **Error envelope** — errors use `HTTPException(status.HTTP_*, detail=...)` and are serialised as `{"detail": "<message>"}`. There is no custom error hierarchy.

---

### `GET /session/{session_id}` — poll session status

Returns the current state of a session. This also refreshes the server's
`last_seen_at` for the session, so polling doubles as a weak keep-alive for
waiting sessions. <!-- trace: neops_remote_lab/server.py:312 -->

**Path parameter** — `session_id`: the uuid returned by `POST /session`.

**Response** — `200 OK`, `SessionStatusResponseDto`:

| Field | Type | Description |
|---|---|---|
| `status` | `"waiting"` or `"active"` | Current session state |
| `position` | integer | Queue position (0 means at the head / ACTIVE) |

**Errors**:

| Status | Condition |
|---|---|
| 404 | No session with that id is tracked |

=== "cURL"

    ```bash
    curl -s "$BASE_URL/session/$SESSION_ID"
    ```

=== "Expected output"

    ```json
    {"status": "waiting", "position": 2}
    ```

---

### `DELETE /session/{session_id}` — end a session

Removes the session from tracking structures. If the session was `ACTIVE` the
server also tears down its lab and promotes the next waiting session to
ACTIVE. <!-- trace: neops_remote_lab/server.py:348 -->

**Response** — `204 No Content`.

**Errors**:

| Status | Condition |
|---|---|
| 404 | Session id unknown |

During server shutdown the endpoint returns 204 even for an unknown id so
clients can clean up gracefully.

=== "cURL"

    ```bash
    curl -s -X DELETE "$BASE_URL/session/$SESSION_ID"
    ```

---

### `POST /session/heartbeat` — keep a session alive

Refreshes `last_seen_at` for the session in the `X-Session-ID` header and
returns 204 — or 404 if the session is unknown. The endpoint only checks
that the session exists; it does **not** require the session to be ACTIVE,
so both WAITING and ACTIVE sessions can heartbeat. <!-- trace: neops_remote_lab/server.py:488 -->

An ACTIVE session must be heartbeated within the 300 s active-stale
timeout; a WAITING session within the 600 s waiting-stale timeout — miss
either and the server reaps the session, and (if ACTIVE) frees its lab. <!-- trace: neops_remote_lab/server.py:95 -->

!!! info "The fixture does this for you"
    The session-scoped `remote_lab_client` fixture pings heartbeat in the
    background. You only need to send heartbeats explicitly when you use
    [`RemoteLabClient`](../20-client/20-python-client.md) directly from non-pytest code.

**Headers**:

| Header | Required | Description |
|---|:-:|---|
| `X-Session-ID` | yes | Session id returned by `POST /session` |

**Response** — `204 No Content`.

**Errors**:

| Status | Condition |
|---|---|
| 404 | Session id unknown |

=== "cURL"

    ```bash
    curl -s -X POST "$BASE_URL/session/heartbeat" \
      -H "X-Session-ID: $SESSION_ID"
    ```

---

## Lab lifecycle

All `/lab/*` endpoints require `X-Session-ID` for an ACTIVE session — see the
contract table above. Responses reference the lab DTOs below.

### `POST /lab` — upload topology and acquire the lab

The most complex endpoint. Accepts a `multipart/form-data` payload with the
topology YAML, optional extra files, and a `reuse` flag. On success it starts
Netlab (`netlab up`) for the topology, or attaches to a running lab when the
content hashes match. <!-- trace: neops_remote_lab/server.py:396 -->

**Request body** — `multipart/form-data`:

| Form field | Type | Required | Description |
|---|---|:-:|---|
| `topology` | file upload | yes | Netlab topology file. Must have a filename ending in `.yml` or `.yaml` (case-insensitive); both are accepted end-to-end. |
| `reuse` | string `"true"` / `"false"` | no | Defaults to `true`. When true and a lab for the same topology is already running, the server increments a reference count and returns the existing lab instead of starting a new one. |
| `extra_files` | file upload (repeatable) | no | Supporting files referenced from the topology (variable files, per-node config, Ansible vars). Saved next to the topology on the server. |

??? info "Topology identity is SHA-256 of content"
    The server identifies topologies by SHA-256 of file content, not filename.
    Two files with different names but identical content share the same lab
    when `reuse=true`. Reference counting drops the lab when the count hits
    zero. See [Lab lifecycle](../10-concepts/30-lab-lifecycle.md).

**Response** — `200 OK`, `AcquireResponseDto`:

| Field | Type | Description |
|---|---|---|
| `reused` | boolean | True when this call attached to an already-running lab rather than starting a new one |
| `devices` | list of `DeviceInfoDto` | One entry per node in the topology |

`DeviceInfoDto` has two fields: `name` (node name as reported by Netlab) and
`raw` (the full `netlab inspect` dictionary for the node — vendor-specific).

**Errors**:

| Status | Condition |
|---|---|
| 400 | Topology file has no filename, or filename does not end in `.yml`/`.yaml` |
| 404 | `X-Session-ID` is unknown |
| 423 | Session is not ACTIVE, **or** the host is running a different topology that `try_acquire` could not attach to <!-- trace: neops_remote_lab/server.py:423 --> |

=== "cURL (minimum)"

    ```bash
    curl -s -X POST "$BASE_URL/lab" \
      -H "X-Session-ID: $SESSION_ID" \
      -F "topology=@tests/topologies/simple_frr.yml" \
      -F "reuse=true"
    ```

=== "cURL (with extra_files)"

    ```bash
    curl -s -X POST "$BASE_URL/lab" \
      -H "X-Session-ID: $SESSION_ID" \
      -F "topology=@tests/topologies/simple_frr.yml" \
      -F "reuse=true" \
      -F "extra_files=@tests/topologies/vars.yml" \
      -F "extra_files=@tests/topologies/host_vars/r1.yml"
    ```

=== "Expected output"

    ```json
    {
      "reused": false,
      "devices": [
        {"name": "r1", "raw": {"ansible_host": "10.0.0.11", "...": "..."}},
        {"name": "r2", "raw": {"ansible_host": "10.0.0.12", "...": "..."}}
      ]
    }
    ```

---

### `POST /lab/release` — decrement the reference count

Releases this session's claim on the lab. When the reference count drops to
zero the lab becomes *idle* but keeps running, available for another session
to attach via `POST /lab` with `reuse=true`. <!-- trace: neops_remote_lab/server.py:436 -->

**Response** — `204 No Content`.

**Errors**:

| Status | Condition |
|---|---|
| 404 | No lab is currently running |
| 404 | `X-Session-ID` is unknown |
| 423 | Session is not ACTIVE |

=== "cURL"

    ```bash
    curl -s -X POST "$BASE_URL/lab/release" \
      -H "X-Session-ID: $SESSION_ID"
    ```

---

### `DELETE /lab` — destroy the lab

Tears down the running lab regardless of its reference count by default.
<!-- trace: neops_remote_lab/server.py:446 -->

**Query parameters**:

| Parameter | Type | Default | Description |
|---|---|---|---|
| `force` | boolean | `true` | When `false`, the request fails with 409 if `ref_count > 0`. |

**Response**:

| Status | When |
|---|---|
| 202 Accepted | Cleanup has been dispatched to the thread pool |
| 204 No Content | No lab was running at the time of the request |

**Errors**:

| Status | Condition |
|---|---|
| 409 | `force=false` and the lab is still in use (`ref_count > 0`) |
| 404 | `X-Session-ID` is unknown |
| 423 | Session is not ACTIVE |

=== "cURL (force)"

    ```bash
    curl -s -X DELETE "$BASE_URL/lab?force=true" \
      -H "X-Session-ID: $SESSION_ID"
    ```

=== "cURL (cooperative)"

    ```bash
    curl -s -X DELETE "$BASE_URL/lab?force=false" \
      -H "X-Session-ID: $SESSION_ID"
    ```

---

### `GET /lab/devices` — list devices in the running lab

Shortcut to the device list without returning the full lab status. Useful after
`POST /lab` if the caller wants to re-fetch device info. <!-- trace: neops_remote_lab/server.py:462 -->

**Response** — `200 OK`, `list[DeviceInfoDto]` (see `POST /lab` response).

**Errors**:

| Status | Condition |
|---|---|
| 404 | No lab is running |
| 404 | `X-Session-ID` is unknown |
| 423 | Session is not ACTIVE |

=== "cURL"

    ```bash
    curl -s "$BASE_URL/lab/devices" \
      -H "X-Session-ID: $SESSION_ID"
    ```

---

## End-to-end cURL walk-through

Combine the endpoints above into a full session:

```bash title="examples/curl/end_to_end_session.sh"
--8<-- "examples/curl/end_to_end_session.sh"
```

---

## Endpoints not documented here

Callers should not depend on the following; they exist but are classed as
internal or unstable:

- `GET /healthz` — liveness probe (returns 204). Use it from container orchestration, not from application code.
- `GET /debug/health` — verbose diagnostic endpoint. Returns queue length,
  session count, and uptime. Intended for development; may change without
  notice.
- `GET /active-session` — returns the currently ACTIVE session's id. Useful
  during debugging; not part of the stable contract.
- `GET /lab` — lab status with device list. Overlaps with `GET /lab/devices`
  and `POST /lab` response. Reserved for introspection use.

If you need one of these for a concrete use case, open an issue so the
contract can be promoted.

---

## See also

- [Session queue](../10-concepts/20-session-queue.md) — FIFO semantics, stale-sweep timeouts, and 423 responses
- [Lab lifecycle](../10-concepts/30-lab-lifecycle.md) — reference counting, SHA identity, and teardown
- [Configuration](20-configuration.md) — environment variables and CLI flags for client and server
- [Administration](10-administration.md) — operator runbook and security posture
