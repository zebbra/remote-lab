---
title: Configuration
description: Environment variables that drive the Python client and pytest fixture — REMOTE_LAB_URL plus the three timeout overrides.
tags: [reference, client]
crosslink_defines: []
crosslink_references: []
---

# Configuration

Four environment variables. One required (`REMOTE_LAB_URL`); three optional timeouts. The pytest fixture reads them at session setup; `RemoteLabClient` reads them at construction. Setting them in CI is exactly the same shape as setting them locally.

## The variables

Read by `RemoteLabClient` and the `remote_lab_client` pytest fixture.

| Variable | Default | Consumed at | Effect |
|---|---|---|---|
| `REMOTE_LAB_URL` | — (required) | Fixture setup / client construction | Base URL of the Remote Lab Manager. Accepts `http://…` or `https://…`; the client strips a trailing `/` before composing paths. |
| `REMOTE_LAB_REQUEST_TIMEOUT` | `30` (seconds) | Fixture setup | Per-HTTP-request timeout for short operations (create session, status, heartbeat, release). |
| `REMOTE_LAB_SESSION_TIMEOUT` | `600` (seconds) | Fixture setup | How long the client will wait for its session to become ACTIVE in the queue before raising `TimeoutError`. |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | `600` (seconds) | Fixture setup | How long `POST /lab` may take before the HTTP request times out. Netlab can take minutes to bring up a topology; this is deliberately long. |

## Required: `REMOTE_LAB_URL`

`RemoteLabClient` falls back to `os.getenv("REMOTE_LAB_URL")` when no `base_url` is passed to its constructor and raises `ValueError("base_url must be provided …")` if both are missing. <!-- trace: neops_remote_lab/client.py:30 -->

The `remote_lab_client` pytest fixture reads the same variable and raises `RuntimeError("REMOTE_LAB_URL not set. …")` at fixture setup when it is unset. <!-- trace: neops_remote_lab/testing/fixture.py:32 -->

```bash
# On the test-runner host
export REMOTE_LAB_URL="http://lab.internal:8000"
```

## Optional: the three timeout variables

The pytest fixture passes any of these that are set through to the client constructor as integer seconds. <!-- trace: neops_remote_lab/testing/fixture.py:37 --> Unset variables fall back to the client's defaults (`30` / `600` / `600`).

```bash
# Test runner
export REMOTE_LAB_REQUEST_TIMEOUT=60
export REMOTE_LAB_SESSION_TIMEOUT=1200
export REMOTE_LAB_ACQUISITION_TIMEOUT=1800
```

When to raise each:

| Variable | When to raise it |
|---|---|
| `REMOTE_LAB_REQUEST_TIMEOUT` | Individual HTTP requests time out on a slow link. |
| `REMOTE_LAB_SESSION_TIMEOUT` | Queue waits regularly exceed the default 600 s (multiple CI jobs sharing one server). |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | Large topologies where `netlab up` takes more than 10 minutes. |

!!! warning "Client and server session timeouts must agree"
    The server independently evicts stale sessions: `_WAITING_SESSION_TIMEOUT` is 600 s and `_ACTIVE_SESSION_STALE` is 300 s. <!-- trace: neops_remote_lab/server.py:95 --> If your client `REMOTE_LAB_SESSION_TIMEOUT` is longer than 600 s, the server will drop your waiting session before the client gives up — your CI sees a confusing timeout error. Coordinate with the operator before raising client-side timeouts past the server defaults.

??? info "Direct client use bypasses the fixture's env-var handling"
    If you instantiate `RemoteLabClient` directly (e.g., from a helper script), the client defaults apply regardless of these env vars — pass the timeouts as keyword arguments instead. See the [`RemoteLabClient` reference](20-python-client.md).

## Not wired: `REMOTE_LAB_TOKEN`

The variable is **not consumed** by either the client or the server. Setting it has no effect; do not rely on it as an access boundary. The service has no HTTP authentication — see [Security model](../30-server/30-security.md).

## See also

- **[Pytest Fixtures](10-pytest-fixtures.md)** — the consumer that drives these variables in test setup.
- **[Python Client](20-python-client.md)** — the constructor arguments that mirror these variables and which take precedence when you instantiate the client directly.
- **[CI quickstart](../getting-started/40-ci.md)** — how the same variables wire into GitHub Actions, GitLab CI, and Jenkins pipelines.
- **[Server-side configuration](../30-server/20-configuration.md)** — the CLI flags and the one server env var (`NEOPS_NETLAB_STREAM_OUTPUT`).
