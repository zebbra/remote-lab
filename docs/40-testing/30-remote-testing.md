---
page_purpose: how-to
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# Remote Lab Testing

<!-- trace: neops_remote_lab/testing/fixture.py:34 -->
Remote mode is the only mode `remote_lab_fixture` supports. Set `REMOTE_LAB_URL` to point the session-scoped `remote_lab_client` fixture at your server; the fixture raises `RuntimeError` at test setup if the variable is missing (`fixture.py:32-34`). For local-only Netlab without a server, see [Local Lab Testing](20-local-testing.md) for the direct `LabManager` pattern.

## Activating Remote Mode

```bash
export REMOTE_LAB_URL=http://<server-host>:8000
```

With this variable set, `remote_lab_fixture()` creates fixtures that depend on the session-scoped `remote_lab_client` fixture, which manages the HTTP connection lifecycle. If `REMOTE_LAB_URL` is not set, the `remote_lab_client` fixture raises `RuntimeError` immediately -- failing fast rather than letting tests run against nothing.

## Session Lifecycle

When pytest starts, the `remote_lab_client` fixture initializes a `RemoteLabClient` that follows this sequence:

1. **Create session** -- `POST /session` returns a `session_id` and queue position
2. **Wait for activation** -- polls `GET /session/{id}` every 5 seconds until `status` becomes `active`. If another session is ahead in the queue, your client waits
3. **Acquire lab** -- each test fixture calls `client.acquire()`, which uploads the topology to `POST /lab` and blocks until the lab is ready
4. **Release lab** -- on fixture teardown, `client.release()` decrements the server's reference count
5. **Close session** -- at the end of the pytest session (or via `atexit`), `client.close()` calls `DELETE /session/{id}` to end the session and free resources

<!-- trace: neops_remote_lab/server.py:481 -->
<!-- trace: neops_remote_lab/server.py:318 -->
Any `POST /lab`, `POST /lab/release`, or `GET /lab*` request updates the server's `last_seen_at` timestamp for the session -- the `X-Session-ID`-authenticated endpoints are the implicit keep-alive path during normal test execution. `GET /session/{id}` polls also refresh `last_seen_at` (server.py:318), which is why a session that keeps checking its queue position rarely goes stale.

!!! note "Long-pause tests"
    If your test harness has setup or teardown gaps longer than `_ACTIVE_SESSION_STALE` (300 s) between lab traffic, send explicit `POST /session/heartbeat` pings to avoid being dropped. <!-- trace: neops_remote_lab/server.py:481-492 --> The `/session/heartbeat` endpoint is a no-op on state -- it updates `last_seen_at` and returns `204`. `RemoteLabClient` does not call it automatically; the pytest fixture layer (or your own wrapper) owns that cadence. See the [REST API reference -- heartbeat](../20-server/10-rest-api.md) for the endpoint schema.

For details on the session queue and promotion logic, see [Session Queue](../10-concepts/20-session-queue.md).

## Topology Upload

When a fixture calls `client.acquire()`, the client reads the topology `.yml` file from your local filesystem and uploads it as a `multipart/form-data` POST to the server. The server copies it to a temp directory and runs `netlab up` there.

Topology matching on the server uses **content hash** -- the same matching strategy as local mode. If two tests use topologies with identical content, the server reuses the running lab (when `reuse_lab=True`) regardless of the local filename.

## Test Ordering

The ordering plugin groups tests by their `remote_lab_fixture` so that all tests sharing a topology run consecutively. This minimizes lab teardown/rebuild cycles on the server. Run with log output to see the computed order:

```bash
pytest -s --log-cli-level=INFO
```

The plugin logs a structured table showing fixture groups, topology paths, and test order. See [Pytest Fixtures -- Test Ordering Plugin](../30-client/20-pytest-fixtures.md#test-ordering-plugin) for details.

## Timeout Tuning

The client has three independent timeouts. Override them via environment variables when defaults do not fit your situation. Highlights below -- see [Configuration -- Environment Variables](../20-server/20-configuration.md#environment-variables) for the canonical defaults table:

| Variable | When to adjust |
|----------|----------------|
| `REMOTE_LAB_REQUEST_TIMEOUT` | Increase if individual HTTP requests time out on slow networks |
| `REMOTE_LAB_SESSION_TIMEOUT` | Increase if your queue wait regularly exceeds 10 minutes (multiple CI jobs sharing one server) |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | Increase for large topologies where `netlab up` takes more than 10 minutes |

Example for a CI pipeline with large topologies and high queue contention:

```bash
export REMOTE_LAB_URL=http://lab-server:8000
export REMOTE_LAB_SESSION_TIMEOUT=1200     # 20 min queue wait
export REMOTE_LAB_ACQUISITION_TIMEOUT=900  # 15 min lab startup
```

The server also has its own stale-session timeouts (300s heartbeat, 600s waiting). If your client timeouts are longer than the server's, the server may drop your session before the client gives up. Coordinate with your server operator -- see [Configuration -- Server Constants](../20-server/20-configuration.md#server-constants).

## HTTP Retry Behavior

`RemoteLabClient` configures automatic retries for transient failures:

- Retries up to **3 times** on status codes `429`, `500`, `502`, `503`, `504`
- Uses exponential backoff (factor of 1 second)
- Only retries safe methods (`GET`, `HEAD`, `OPTIONS`, `DELETE`) -- `POST` requests (including lab acquisition) are **not retried** automatically to avoid duplicate side effects
- When `POST /lab` returns `423 Locked` (lab busy), the client retries in a 5-second loop until the lab becomes available

## CI Integration

### Basic Pipeline Step

```yaml
# GitHub Actions example
- name: Run integration tests
  env:
    REMOTE_LAB_URL: http://lab-server:8000
    REMOTE_LAB_SESSION_TIMEOUT: "1200"
  run: pytest tests/ -q
```

### Tips for CI

- **VPN connectivity** -- your CI runner must reach the Remote Lab server and the lab subnet. If you use Headscale/Tailscale, ensure the runner has a valid Tailscale session. See [Deployment](../50-deployment/index.md).
- **Parallel jobs** -- multiple CI jobs can target the same server. The session queue serializes access automatically. Increase `REMOTE_LAB_SESSION_TIMEOUT` to accommodate queue depth.
- **Fail fast** -- if `REMOTE_LAB_URL` points to an unreachable server, the client fails at session creation rather than mid-test. You will see a `ConnectionError` in the first seconds of the test run.
- **Cleanup on cancellation** -- if a CI job is killed mid-run, the `atexit` handler attempts to close the session. If the process is hard-killed (`SIGKILL`), the server's stale session cleanup reclaims the slot after the heartbeat timeout (default 300s).
- **Log level** -- set `--log-cli-level=INFO` in CI to capture session creation, queue position, and lab acquisition events in build logs. This helps when diagnosing timeout issues after the fact.

## Verifying Server Reachability

Before running your full test suite, confirm connectivity:

```bash
# Liveness check
curl -s -o /dev/null -w "%{http_code}" http://<server-host>:8000/healthz
# Expected: 204

# Detailed server status
curl -s http://<server-host>:8000/debug/health | jq .
```

If the liveness check fails, the server is down or unreachable. See [Debugging and Troubleshooting](40-debugging.md) for next steps.
