---
title: Configuration
description: CLI flags and the one environment variable that control the neops-remote-lab server. For client-side configuration, see Use from Python → Configuration.
tags: [reference, operator, server]
crosslink_defines: []
crosslink_references: []
---

# Configuration

*Server-side knobs only. CLI flags on the entry point and one environment variable. Client config lives under [Use from Python](../20-client/30-configuration.md).*

Server-side knobs only: a handful of CLI flags on the `neops-remote-lab` entry point and a single environment variable that toggles Netlab subprocess streaming. Client-side configuration (`REMOTE_LAB_URL` plus the three timeouts) lives on its own page under [Use from Python → Configuration](../20-client/30-configuration.md).

## Server CLI flags

The `neops-remote-lab` entry point is defined in `neops_remote_lab/__main__.py:main()` and parses the following flags via argparse. <!-- trace: neops_remote_lab/__main__.py:148 -->

| Flag | Default | Description |
|---|---|---|
| `--host <addr>` | `0.0.0.0` | Interface to bind. The default binds on all interfaces — only appropriate on trusted networks (see [Security model](30-security.md)). |
| `--port <int>` | `8000` | TCP port. |
| `--log-level <level>` | `INFO` | Python logging level applied to the remote-lab loggers. Case-insensitive (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `--log-config <path>` | `logging_config.yaml` | Path to a YAML logging config. If the path does not exist, the packaged default is used (`neops_remote_lab/logging_config.yaml`). |
| `--debug` | off | Enables debug logging and streams Netlab output (see below). |
| `--version` | — | Print version and exit. |

### The `--debug` shortcut

`--debug` performs two side effects on top of normal startup: <!-- trace: neops_remote_lab/__main__.py:163 -->

1. Overrides `--log-level` to `DEBUG`.
2. Exports `NEOPS_NETLAB_STREAM_OUTPUT=1` into the process environment, so Netlab subprocess output streams to the log in real time.

Equivalent to:

```bash
NEOPS_NETLAB_STREAM_OUTPUT=1 neops-remote-lab --log-level DEBUG --port 8000
```

### Launch examples

=== "Default"

    ```bash
    neops-remote-lab
    ```

    Binds to `0.0.0.0:8000` with `INFO` logging and the packaged logging config.

=== "Verbose investigation"

    ```bash
    neops-remote-lab --debug --port 8000
    ```

    DEBUG logging plus live Netlab output. Useful when a topology fails to come up and you want to watch `netlab up` in the server log.

=== "Bound to VPN only"

    ```bash
    neops-remote-lab --host 10.0.0.2 --port 8000
    ```

    Bind to a specific interface — preferred when the host has a public NIC you do not want the server reachable on.

=== "Custom logging config"

    ```bash
    neops-remote-lab --log-config /etc/neops/remote-lab-logging.yaml
    ```

## Server environment variable

### `NEOPS_NETLAB_STREAM_OUTPUT`

When set to the string `"1"`, `run_netlab` unconditionally enables line-by-line streaming of Netlab subprocess output into the server log at DEBUG level. <!-- trace: neops_remote_lab/netlab/connector.py:99 -->

| Value | Effect |
|---|---|
| `"1"` | Stream Netlab stdout/stderr live to the logger |
| unset or anything else | Capture Netlab output and log only on non-zero exit code |

The server sets this automatically when you launch it with `--debug`. Export it manually for one-off investigations without changing the log level.

## Server startup prerequisites

The entry point performs two pre-flight checks before binding the HTTP port:

- **Single-instance lock** — see [Administration → Single-instance filelock](10-administration.md#single-instance-filelock).
- **Netlab CLI on PATH** — if `shutil.which("netlab")` returns `None` the server logs the install URL and exits with `SystemExit(1)` before starting. <!-- trace: neops_remote_lab/__main__.py:206 --> Install Netlab on the host before starting the server — see [Netlab host setup](../40-deployment/10-netlab-host-setup.md).

## What you almost never need to change

- **Server cleanup cadence** — hard-coded in `server.py`: `_SESSION_CLEANUP_INTERVAL = 5`, `_WAITING_SESSION_TIMEOUT = 600`, `_ACTIVE_SESSION_STALE = 300`. These are not exposed as flags because changing them shifts the FIFO contract that clients depend on; see [Session Queue](../10-concepts/20-session-queue.md) for the reasoning.
- **Netlab instance name** — the server always uses the `default` Netlab instance and cleans up stale defaults at startup.

If you believe you need to change one of these, open an issue — the one-size-fits-all defaults are deliberate.

## Client-side configuration

Client environment variables (`REMOTE_LAB_URL` plus the three timeout overrides) live on their own page: [Use from Python → Configuration](../20-client/30-configuration.md). The pytest fixture and `RemoteLabClient` read those at setup time on the test-runner host, not on the server.

## See also

- **[REST API](40-rest-api.md)** — endpoints served on `--host`:`--port`.
- **[Operator runbook](10-administration.md)** — install, systemd, stale-lock recovery, stuck-lab cleanup.
- **[Security model](30-security.md)** — the threat model the `--host` recommendation above is built on top of.
- **[Client config](../20-client/30-configuration.md)** — client environment variables (`REMOTE_LAB_URL` and the three timeout overrides).
