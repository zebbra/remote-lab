---
title: Configuration
description: Environment variables, CLI flags, and runtime switches that control the Remote Lab client and server.
tags: [reference, operator, server]
crosslink_defines: []
crosslink_references: []
---

# Configuration

The Remote Lab Manager reads its configuration from three places:

1. **Client-side environment variables** — consumed by `RemoteLabClient` and the
   pytest fixtures on the test-runner host.
2. **Server-side CLI flags** — consumed by the `neops-remote-lab` entry point
   on the lab host.
3. **Server-side environment variables** — a single toggle affecting Netlab
   subprocess output.

!!! danger "Bearer authentication is NOT wired"
    The `REMOTE_LAB_TOKEN` code path in `RemoteLabClient.__init__` is
    **commented out**. <!-- trace: neops_remote_lab/client.py:46 --> Setting
    this environment variable does nothing. No endpoint enforces bearer
    authentication. See [Administration → Security posture](30-administration.md#security-posture)
    before exposing the server.

---

## Client environment variables

Read by `RemoteLabClient` and the `remote_lab_client` pytest fixture.

| Variable | Default | Consumed at | Effect |
|---|---|---|---|
| `REMOTE_LAB_URL` | — (required) | Fixture setup / client construction | Base URL of the Remote Lab Manager. Accepts `http://…` or `https://…`; the client strips a trailing `/` before composing paths. |
| `REMOTE_LAB_REQUEST_TIMEOUT` | `30` (seconds) | Fixture setup | Per-HTTP-request timeout for short operations (create session, status, heartbeat, release). |
| `REMOTE_LAB_SESSION_TIMEOUT` | `600` (seconds) | Fixture setup | How long the client will wait for its session to become ACTIVE in the queue before raising `TimeoutError`. |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | `600` (seconds) | Fixture setup | How long `POST /lab` may take before the HTTP request times out. Netlab can take minutes to bring up a topology; this is deliberately long. |

### Required: `REMOTE_LAB_URL`

`RemoteLabClient` falls back to `os.getenv("REMOTE_LAB_URL")` when no
`base_url` is passed to its constructor and raises
`ValueError("base_url must be provided …")` if both are missing. <!-- trace: neops_remote_lab/client.py:30 -->

The `remote_lab_client` pytest fixture reads the same variable and raises
`RuntimeError("REMOTE_LAB_URL not set. …")` at fixture setup when it is unset.
<!-- trace: neops_remote_lab/testing/fixture.py:32 -->

```bash
# On the test-runner host
export REMOTE_LAB_URL="http://lab.internal:8000"
```

### Optional: the three timeout variables

The pytest fixture passes any of these that are set through to the client
constructor as integer seconds. <!-- trace: neops_remote_lab/testing/fixture.py:37 -->
Unset variables fall back to the client's defaults (`30` / `600` / `600`).

```bash
# Test runner
export REMOTE_LAB_REQUEST_TIMEOUT=60
export REMOTE_LAB_SESSION_TIMEOUT=1200
export REMOTE_LAB_ACQUISITION_TIMEOUT=1800
```

??? info "Direct client use bypasses the fixture's env-var handling"
    If you instantiate `RemoteLabClient` directly (e.g., from a helper script)
    the client defaults apply regardless of these env vars — pass the timeouts
    as keyword arguments instead. See the
    [`RemoteLabClient` reference](../client/20-python-client.md).

### Not wired: `REMOTE_LAB_TOKEN`

Referenced inside a comment in `client.py`; the `Authorization: Bearer`
header-injection block is inactive. Setting this variable does nothing. Do not
rely on it as an access boundary.

---

## Server environment variables

### `NEOPS_NETLAB_STREAM_OUTPUT`

When set to the string `"1"`, `run_netlab` unconditionally enables
line-by-line streaming of Netlab subprocess output into the server log at
DEBUG level. <!-- trace: neops_remote_lab/netlab/connector.py:99 -->

| Value | Effect |
|---|---|
| `"1"` | Stream Netlab stdout/stderr live to the logger |
| unset or anything else | Capture Netlab output and log only on non-zero exit code |

The server sets this automatically when you launch it with `--debug` — see
below. You can also export it manually for one-off investigations without
changing the log level.

---

## Server CLI flags

The `neops-remote-lab` entry point is defined in
`neops_remote_lab/__main__.py:main()` and parses the following flags via
argparse. <!-- trace: neops_remote_lab/__main__.py:148 -->

| Flag | Default | Description |
|---|---|---|
| `--host <addr>` | `0.0.0.0` | Interface to bind. The default binds on all interfaces — only appropriate on trusted networks (see [Administration](30-administration.md#security-posture)). |
| `--port <int>` | `8000` | TCP port. |
| `--log-level <level>` | `INFO` | Python logging level applied to the remote-lab loggers. Case-insensitive (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `--log-config <path>` | `logging_config.yaml` | Path to a YAML logging config. If the path does not exist, the packaged default is used (`neops_remote_lab/logging_config.yaml`). |
| `--debug` | off | Enables debug logging and streams Netlab output (see below). |
| `--version` | — | Print version and exit. |

### The `--debug` shortcut

`--debug` performs two side effects on top of normal startup: <!-- trace: neops_remote_lab/__main__.py:163 -->

1. Overrides `--log-level` to `DEBUG`.
2. Exports `NEOPS_NETLAB_STREAM_OUTPUT=1` into the process environment, so
   Netlab subprocess output streams to the log in real time.

Equivalent to:

```bash
NEOPS_NETLAB_STREAM_OUTPUT=1 neops-remote-lab --log-level DEBUG --port 8000
```

### Launch examples

=== "Default"

    ```bash
    neops-remote-lab
    ```

    Binds to `0.0.0.0:8000` with `INFO` logging and the packaged logging
    config.

=== "Verbose investigation"

    ```bash
    neops-remote-lab --debug --port 8000
    ```

    DEBUG logging plus live Netlab output. Useful when a topology fails to
    come up and you want to watch `netlab up` in the server log.

=== "Bound to VPN only"

    ```bash
    neops-remote-lab --host 10.0.0.2 --port 8000
    ```

    Bind to a specific interface — preferred when the host has a public NIC
    you do not want the server reachable on.

=== "Custom logging config"

    ```bash
    neops-remote-lab --log-config /etc/neops/remote-lab-logging.yaml
    ```

---

## Server startup prerequisites

The entry point performs two pre-flight checks before binding the HTTP port:

- **Single-instance lock** — see [Administration → Single-instance filelock](30-administration.md#single-instance-filelock).
- **Netlab CLI on PATH** — if `shutil.which("netlab")` returns `None` the
  server logs the install URL and exits with `SystemExit(1)` before starting.
  <!-- trace: neops_remote_lab/__main__.py:206 --> Install Netlab on the host
  before starting the server — see
  [Netlab host setup](../deployment/10-netlab-host-setup.md).

---

## What you almost never need to change

- **Server cleanup cadence** — hard-coded in `server.py`:
  `_SESSION_CLEANUP_INTERVAL = 5`, `_WAITING_SESSION_TIMEOUT = 600`,
  `_ACTIVE_SESSION_STALE = 300`. These are not exposed as flags because
  changing them shifts the FIFO contract that clients depend on; see
  [Session queue](../concepts/20-session-queue.md) for the reasoning.
- **Netlab instance name** — the server always uses the `default` Netlab
  instance and cleans up stale defaults at startup.

If you believe you need to change one of these, open an issue — the
one-size-fits-all defaults are deliberate.

---

## See also

- [REST API](10-rest-api.md) — endpoints served on `--host`:`--port`
- [Administration](30-administration.md) — operator runbook, stuck labs, security posture
- [`RemoteLabClient`](../client/20-python-client.md) — constructor arguments that mirror the client env vars
- [pytest fixtures](../client/10-pytest-fixtures.md) — how `remote_lab_client` consumes the env vars above
