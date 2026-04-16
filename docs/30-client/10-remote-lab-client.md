---
page_purpose: reference
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# RemoteLabClient API

`RemoteLabClient` is a session-aware HTTP client for the Remote Lab server. It manages the full session lifecycle -- creating a session, waiting in the queue until it becomes active, acquiring and releasing labs, and closing the session on teardown.

Most users do not instantiate this class directly. The [`remote_lab_client` pytest fixture](20-pytest-fixtures.md) creates and manages a single instance for the entire test session. Use `RemoteLabClient` directly only when you need programmatic lab access outside of pytest.

## Constructor

```python
from neops_remote_lab.client import RemoteLabClient

client = RemoteLabClient(
    base_url="http://lab-host:8000",
    request_timeout=30,
    session_timeout=600,
    lab_acquisition_timeout=600,
)
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `base_url` | `str` | *(required)* | Server URL. Falls back to `REMOTE_LAB_URL` env var if the passed value is falsy. Raises `ValueError` if neither is set. |
| `request_timeout` | `int` | `30` | Timeout in seconds for short HTTP requests (session creation, status polling, release, destroy, close). |
| `session_timeout` | `int` | `600` | Maximum seconds to wait for the session to reach `ACTIVE` state in the queue. Raises `TimeoutError` if exceeded. |
| `lab_acquisition_timeout` | `int` | `600` | Timeout in seconds for the `POST /lab` request, which blocks while Netlab brings up the topology. |

### Initialization Sequence

The constructor performs three blocking operations before returning:

1. **Creates an HTTP session** with retry logic and connection pooling (see [HTTP Retry Strategy](#http-retry-strategy) below).
2. **Creates a server session** via `POST /session`, obtaining a `session_id` and initial queue position.
3. **Waits for the session to become active** by polling `GET /session/{id}` every 5 seconds until the status is `ACTIVE`, or until `session_timeout` is exceeded.

If any step fails, the constructor raises and the client is not usable. There is no partial initialization state.

## Public Methods

### `acquire(topology, reuse)`

Uploads a topology file and acquires a lab. Blocks until the lab is ready or the server returns an error.

```python
acquire(topology: pathlib.Path, reuse: bool) -> list[DeviceInfoDto]
```

| Parameter | Type | Description |
|-----------|------|-------------|
| `topology` | `pathlib.Path` | Path to a Netlab topology `.yml` file. The file is uploaded as a multipart form field. |
| `reuse` | `bool` | Whether to reuse an existing lab running the same topology. See [Lab Lifecycle -- Reuse vs. Exclusive Access](../10-concepts/30-lab-lifecycle.md#reuse-vs-exclusive-access). |

**Returns:** `list[DeviceInfoDto]` -- one entry per device in the lab. Each `DeviceInfoDto` has:

- `name: str` -- node name as reported by Netlab
- `raw: dict[str, Any]` -- the full `netlab inspect` dictionary for the node

**Behavior:**

- Sends `POST /lab` with the topology file as a multipart upload and `reuse` as a form field.
- If the server responds with `423 Locked` (lab is busy with a different topology or an exclusive session), the client retries every 5 seconds indefinitely until the lab becomes available.
- The request timeout for this call is `lab_acquisition_timeout` (default 600s), which must accommodate `netlab up` startup time.
- On any other HTTP error or connection failure, raises `requests.exceptions.RequestException`.

### `release()`

Releases the current lab, decrementing the server-side reference count.

```python
release() -> None
```

Sends `POST /lab/release`. Accepts `204` (released) and `404` (no lab running) as success -- both mean the client no longer holds a reference. Logs and suppresses other errors rather than raising, since release is typically called during teardown where exceptions are unhelpful.

### `destroy(force)`

Destroys the current lab, tearing down the Netlab topology.

```python
destroy(force: bool = True) -> None
```

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `force` | `bool` | `True` | When `True`, destroys the lab regardless of reference count. |

Sends `DELETE /lab` with `force` as a query parameter. Accepts `202` (teardown initiated) and `204` (torn down) as success. Like `release()`, logs and suppresses errors during teardown.

### `close()`

Ends the session and releases all server-side resources.

```python
close() -> None
```

Sends `DELETE /session/{session_id}`. After this call, the client's `session_id` is cleared and no further operations are possible. Accepts `204` (deleted) and `404` (already gone) as success. Suppresses connection errors with a warning log, since the server may already be shut down when `close()` runs during interpreter exit.

`close()` is safe to call multiple times -- subsequent calls are no-ops if `session_id` is already empty.

## Context Manager Support

`RemoteLabClient` does not implement `__enter__`/`__exit__`. The [`remote_lab_client` pytest fixture](20-pytest-fixtures.md) manages lifecycle via a generator (`yield` / `finally`) and an `atexit` handler instead.

If you use the client outside of pytest, manage cleanup explicitly:

```python
client = RemoteLabClient(base_url="http://lab-host:8000")
try:
    devices = client.acquire(Path("topology.yml"), reuse=True)
    # ... use devices ...
    client.release()
finally:
    client.close()
```

## HTTP Retry Strategy

The internal `requests.Session` is configured with `urllib3.util.retry.Retry`:

| Setting | Value | Effect |
|---------|-------|--------|
| `total` | `3` | Up to 3 retries per request |
| `status_forcelist` | `[429, 500, 502, 503, 504]` | Retry on these status codes |
| `backoff_factor` | `1` | Wait 1s, 2s, 4s between retries |
| `allowed_methods` | `["HEAD", "GET", "OPTIONS", "DELETE"]` | Only idempotent methods are retried automatically |

Connection pooling is configured with `pool_connections=5` and `pool_maxsize=10`. The retry adapter is mounted on both `http://` and `https://` schemes.

Note that `POST` is not in `allowed_methods`, so `acquire()` and `release()` calls are **not** automatically retried by the adapter. The `acquire()` method implements its own retry loop for `423 Locked` responses.

## Queue Wait Logic

During initialization, `_wait_for_active_session()` polls the session status with these behaviors:

- **Poll interval:** 5 seconds between successful status checks.
- **Transient error handling:** On connection errors or 5xx responses, retries with exponential backoff (2^n seconds, capped at 30s). Gives up after 10 consecutive transient failures.
- **Non-retriable errors:** HTTP 4xx responses (except those handled by the retry adapter) cause an immediate raise -- these indicate a client-side problem.
- **Timeout:** Raises `TimeoutError` if the session does not become `ACTIVE` within `session_timeout` seconds.

The queue position is logged at `INFO` level on each poll, so you can monitor wait progress in test output.

## Error Reference

| Exception | When | Cause |
|-----------|------|-------|
| `ValueError` | Constructor | `base_url` is falsy and `REMOTE_LAB_URL` env var is not set |
| `TimeoutError` | Constructor | Session did not become `ACTIVE` within `session_timeout` |
| `requests.exceptions.RequestException` | Constructor, `acquire()` | HTTP connection failure or non-retriable server error |
| `requests.exceptions.HTTPError` | Constructor, `acquire()` | Server returned an error status (after retries are exhausted) |

The `release()`, `destroy()`, and `close()` methods log errors but do not raise, since they run during teardown where exceptions propagate poorly.

## Environment Variables

These environment variables affect `RemoteLabClient` behavior:

| Variable | Used By | Purpose |
|----------|---------|---------|
| `REMOTE_LAB_URL` | Constructor | Fallback for `base_url` when the parameter is falsy |

Additional environment variables (`REMOTE_LAB_REQUEST_TIMEOUT`, `REMOTE_LAB_SESSION_TIMEOUT`, `REMOTE_LAB_ACQUISITION_TIMEOUT`) are read by the [`remote_lab_client` fixture](20-pytest-fixtures.md), not by the client class itself. The client accepts these values as constructor parameters.
