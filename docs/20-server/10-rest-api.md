---
page_purpose: reference
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: intermediate
---

# REST API

The Remote Lab server exposes a REST API built with FastAPI. All endpoints use JSON unless noted otherwise. An interactive OpenAPI UI is available at `/docs` on the running server (e.g., `http://localhost:8000/docs`).

## Authentication

There is no traditional authentication. Access control is session-based: clients create a session and then pass their session ID in the `X-Session-ID` header on subsequent requests. Endpoints that manage labs require a session in the `ACTIVE` state; non-active sessions receive `423 Locked`.

## Session Management

### POST /session

Create a new session and enter the queue.

**Request:** No body required.

**Response:** `201 Created`

```json
{
  "session_id": "a1b2c3d4-...",
  "position": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | UUID assigned to the new session |
| `position` | `int` | Zero-based queue position. `0` means the session is immediately `ACTIVE` |

If no other sessions exist, the new session is promoted to `ACTIVE` immediately. Otherwise it enters the queue in `WAITING` state.

```bash
curl -s -X POST http://localhost:8000/session
```

---

### GET /session/{session_id}

Poll the status and queue position of a session. Also serves as an implicit heartbeat -- the server updates `last_seen_at` on each call.

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `string` | UUID of the session |

**Response:** `200 OK`

```json
{
  "status": "waiting",
  "position": 1
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | `"waiting"` or `"active"` |
| `position` | `int` | Zero-based queue position. `0` = active, `1` = next in line, etc. |

**Error responses:**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Session ID does not exist |

```bash
curl -s http://localhost:8000/session/$SESSION_ID
```

---

### GET /active-session

Get the currently active session (the session at the head of the queue).

**Request:** No body or headers required.

**Response:** `200 OK`

```json
{
  "session_id": "a1b2c3d4-...",
  "status": "active",
  "position": 0
}
```

| Field | Type | Description |
|-------|------|-------------|
| `session_id` | `string` | UUID of the active session |
| `status` | `string` | Always `"active"` |
| `position` | `int` | Always `0` |

**Error responses:**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | No sessions in the queue |

```bash
curl -s http://localhost:8000/active-session
```

---

### DELETE /session/{session_id}

End a session. If the session is `ACTIVE`, the server tears down the running lab and promotes the next session in the queue.

**Path parameters:**

| Parameter | Type | Description |
|-----------|------|-------------|
| `session_id` | `string` | UUID of the session to end |

**Response:** `204 No Content`

**Error responses:**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Session ID does not exist |

During server shutdown, deletion succeeds even if lab cleanup fails -- the session is removed regardless.

```bash
curl -s -X DELETE http://localhost:8000/session/$SESSION_ID
```

---

### POST /session/heartbeat

Keep a session alive. The server uses heartbeats to detect stale sessions. Without periodic heartbeats, an active session is reclaimed after the stale timeout (default 300 s). See [Configuration](20-configuration.md) for timeout values.

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Session-ID` | Yes | UUID of the session to keep alive |

**Response:** `204 No Content`

**Error responses:**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Session ID does not exist |

Note: Unlike the `/lab*` endpoints, heartbeat does **not** require the session to be `ACTIVE`. Any tracked session can send heartbeats.

```bash
curl -s -X POST http://localhost:8000/session/heartbeat \
     -H "X-Session-ID: $SESSION_ID"
```

---

## Lab Management

All lab endpoints require the `X-Session-ID` header with an `ACTIVE` session. Non-active sessions receive `423 Locked`. See [Session Queue](../10-concepts/20-session-queue.md) for how sessions are promoted.

### POST /lab

Upload a topology file and acquire the lab. This is a `multipart/form-data` request. For the full contract that `topology` and `extra_files` must satisfy (Netlab YAML envelope, supported providers/modules, subdirectory preservation in `extra_files`), see [Topology Format](../10-concepts/40-topology-format.md).

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Session-ID` | Yes | UUID of the active session |

**Form fields:**

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `topology` | `file` | Yes | A `.yml` or `.yaml` Netlab topology file |
| `reuse` | `boolean` | No | Whether to reuse an already-running lab with the same topology. Default: `true` |
| `extra_files` | `file` (repeatable) | No | Additional files (variable files, configs) uploaded alongside the topology |

**Response:** `200 OK`

```json
{
  "reused": false,
  "devices": [
    {
      "name": "router1",
      "raw": { "...": "full netlab inspect output for this node" }
    }
  ]
}
```

| Field | Type | Description |
|-------|------|-------------|
| `reused` | `boolean` | `true` if an existing lab was reused (ref_count > 1) |
| `devices` | `DeviceInfoDto[]` | List of devices in the lab |
| `devices[].name` | `string` | Node name as reported by Netlab |
| `devices[].raw` | `object` | Raw `netlab inspect` dictionary for the node |

**Error responses:**

| Status | Condition |
|--------|-----------|
| `400 Bad Request` | Topology file missing a filename, or not a `.yml`/`.yaml` file |
| `404 Not Found` | Session not found |
| `423 Locked` | Session exists but is not `ACTIVE` (still `WAITING` in queue), or lab is currently busy |

```bash
curl -X POST http://localhost:8000/lab \
     -H "X-Session-ID: $SESSION_ID" \
     -F "topology=@tests/topologies/simple_frr.yml" \
     -F "reuse=true"

# With extra files:
curl -X POST http://localhost:8000/lab \
     -H "X-Session-ID: $SESSION_ID" \
     -F "topology=@tests/topologies/simple_frr.yml" \
     -F "reuse=true" \
     -F "extra_files=@path/to/vars.yml" \
     -F "extra_files=@path/to/config.yml"
```

---

### GET /lab

Get the full status of the current lab, including device list.

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Session-ID` | Yes | UUID of the active session |

**Response:** `200 OK`

```json
{
  "running": true,
  "topology": "/tmp/remote_netlab_upload_.../simple_frr.yml",
  "ref_count": 1,
  "devices": [
    {
      "name": "router1",
      "raw": { "...": "..." }
    }
  ],
  "netlab_status": "..."
}
```

| Field | Type | Description |
|-------|------|-------------|
| `running` | `boolean` | Whether a lab is currently running |
| `topology` | `string \| null` | Path of the running topology file |
| `ref_count` | `int` | How many clients currently hold the lab |
| `devices` | `DeviceInfoDto[]` | List of devices (included because `include_devices=True`) |
| `netlab_status` | `string \| null` | Raw output of `netlab status` if available |

**Error responses:**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Session not found |
| `423 Locked` | Session is not `ACTIVE` |

```bash
curl -s http://localhost:8000/lab -H "X-Session-ID: $SESSION_ID"
```

---

### GET /lab/devices

Get the list of devices in the running lab. A shortcut that returns only the device list.

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Session-ID` | Yes | UUID of the active session |

**Response:** `200 OK`

```json
[
  {
    "name": "router1",
    "raw": { "...": "..." }
  }
]
```

**Error responses:**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Session not found, or no lab running |
| `423 Locked` | Session is not `ACTIVE` |

```bash
curl -s http://localhost:8000/lab/devices -H "X-Session-ID: $SESSION_ID"
```

---

### POST /lab/release

Release the current client's hold on the lab (decrement the reference count). If the ref count drops to zero, the lab becomes idle but remains running for potential reuse.

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Session-ID` | Yes | UUID of the active session |

**Response:** `204 No Content`

**Error responses:**

| Status | Condition |
|--------|-----------|
| `404 Not Found` | Session not found, or no lab running |
| `423 Locked` | Session is not `ACTIVE` |

```bash
curl -s -X POST http://localhost:8000/lab/release \
     -H "X-Session-ID: $SESSION_ID"
```

---

### DELETE /lab

Destroy the running lab. The lab is torn down via `LabManager.cleanup`. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md) for what cleanup entails.

**Headers:**

| Header | Required | Description |
|--------|----------|-------------|
| `X-Session-ID` | Yes | UUID of the active session |

**Query parameters:**

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | `boolean` | `true` | When `false`, fails with `409 Conflict` if the lab has active references (ref_count > 0). When `true` (default), destroys regardless. |

**Response:**

| Status | Condition |
|--------|-----------|
| `202 Accepted` | Lab destruction initiated |
| `204 No Content` | No lab was running (nothing to destroy) |
| `409 Conflict` | `force=false` and the lab still has active references |
| `404 Not Found` | Session not found |
| `423 Locked` | Session is not `ACTIVE` |

```bash
# Force destroy (default)
curl -s -X DELETE http://localhost:8000/lab \
     -H "X-Session-ID: $SESSION_ID"

# Non-force: fails if lab is still in use
curl -s -X DELETE "http://localhost:8000/lab?force=false" \
     -H "X-Session-ID: $SESSION_ID"
```

---

## Health

### GET /healthz

Liveness probe. Returns an empty response if the server is running. Suitable for load balancer or container orchestrator health checks.

**Response:** `204 No Content`

No body is returned. Requests to this endpoint are not logged.

```bash
curl -s -o /dev/null -w "%{http_code}" http://localhost:8000/healthz
# 204
```

---

### GET /debug/health

Detailed health endpoint for debugging server responsiveness. Returns runtime statistics useful during development and troubleshooting.

**Response:** `200 OK`

```json
{
  "status": "ok",
  "timestamp": 1716812096.123,
  "uptime": 3600.5,
  "sessions": 2,
  "queue_length": 2
}
```

| Field | Type | Description |
|-------|------|-------------|
| `status` | `string` | Always `"ok"` |
| `timestamp` | `float` | Current server time (Unix epoch) |
| `uptime` | `float` | Seconds since server started |
| `sessions` | `int` | Total tracked sessions |
| `queue_length` | `int` | Sessions currently in the queue |

```bash
curl -s http://localhost:8000/debug/health | jq .
```

---

## Full Session Workflow Example

A complete cURL workflow from session creation through lab teardown:

```bash
# 1. Create a session
SESSION=$(curl -s -X POST http://localhost:8000/session | jq -r .session_id)

# 2. Poll until the session becomes active
while true; do
  STATUS=$(curl -s http://localhost:8000/session/$SESSION | jq -r .status)
  [[ $STATUS == "active" ]] && break
  sleep 2
done

# 3. Upload topology and acquire the lab
curl -X POST http://localhost:8000/lab \
     -H "X-Session-ID: $SESSION" \
     -F "topology=@tests/topologies/simple_frr.yml" \
     -F "reuse=true"

# 4. Send heartbeats to keep the session alive (in a background loop)
while true; do
  curl -s -X POST http://localhost:8000/session/heartbeat \
       -H "X-Session-ID: $SESSION"
  sleep 60
done &
HEARTBEAT_PID=$!

# 5. Query lab status and devices
curl -s http://localhost:8000/lab -H "X-Session-ID: $SESSION" | jq .
curl -s http://localhost:8000/lab/devices -H "X-Session-ID: $SESSION" | jq .

# 6. Release the lab when done
curl -s -X POST http://localhost:8000/lab/release -H "X-Session-ID: $SESSION"

# 7. End the session
kill $HEARTBEAT_PID
curl -s -X DELETE http://localhost:8000/session/$SESSION
```

## Interactive Documentation

The server auto-generates an OpenAPI (Swagger) UI at `/docs`. Open `http://<host>:<port>/docs` in a browser to explore endpoints, view schemas, and execute test requests directly.
