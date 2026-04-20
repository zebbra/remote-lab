---
page_purpose: reference
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: intermediate
---

# Configuration

The Remote Lab server is configured through CLI flags, environment variables, and an optional YAML logging configuration file. There are no mandatory configuration files -- the server runs with sensible defaults out of the box.

<!-- trace: neops_remote_lab/client.py:1 -->
!!! warning "Internal-trust service"
    <!-- trace: neops_remote_lab/client.py -->
    As of this version, `REMOTE_LAB_TOKEN` and Bearer auth are commented out in `client.py`; the only access boundary on `/lab/*` endpoints is the `X-Session-ID` header of the currently `ACTIVE` session. Deploy only inside networks you trust. See [Production -- Security](../50-deployment/30-production.md#security) for firewall and VPN guidance.

## CLI Flags

Pass these flags when starting the server via `neops-remote-lab` or `python -m neops_remote_lab`.

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `0.0.0.0` | Bind address. `0.0.0.0` listens on all interfaces. |
| `--port` | `8000` | TCP port for the HTTP server. |
| `--log-level` | `INFO` | Logging level. Accepts `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` (case-insensitive). |
| `--log-config` | `logging_config.yaml` | Path to a YAML logging configuration file. If the file does not exist at the given path, the server falls back to the packaged default inside `neops_remote_lab/`. |
| `--debug` | *(off)* | Shortcut that sets `--log-level DEBUG` and enables `NEOPS_NETLAB_STREAM_OUTPUT=1` so Netlab command output is streamed to the console. |
| `--version` | -- | Print the installed version and exit. |

Example:

```bash
neops-remote-lab --host 0.0.0.0 --port 9000 --log-level DEBUG
```

## Environment Variables

### Server-side

| Variable | Description | Default |
|----------|-------------|---------|
| `NEOPS_NETLAB_STREAM_OUTPUT` | When set to `1`, Netlab subprocess output is streamed to the server console. Automatically enabled by `--debug`. | *(unset)* |

### Client-side

These variables are consumed by the `RemoteLabClient` and pytest fixtures, not by the server itself. They are listed here for completeness.

| Variable | Description | Default |
|----------|-------------|---------|
| `REMOTE_LAB_URL` | Base URL of the Remote Lab server (e.g., `http://192.168.1.10:8000`). Required for remote mode. | *(unset)* |
| `REMOTE_LAB_REQUEST_TIMEOUT` | Per-HTTP-request timeout in seconds. | `30` |
| `REMOTE_LAB_SESSION_TIMEOUT` | Maximum seconds the client waits in the session queue before giving up. | `600` |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | Maximum seconds to wait for lab acquisition (topology upload + `netlab up`). | `600` |

See the [Client](../30-client/index.md) section for details on client-side configuration.

## Server Constants

These values are defined at the top of `neops_remote_lab/server.py` and control session cleanup behavior. They are not currently exposed as CLI flags or environment variables -- changing them requires editing the source.

| Constant | Value | Description |
|----------|-------|-------------|
| `_SESSION_CLEANUP_INTERVAL` | `5` seconds | Base interval between cleanup runs. The actual interval adapts: ~5 s when busy (multiple sessions), ~15 s with a single active session, ~30 s when idle. |
| `_WAITING_SESSION_TIMEOUT` | `600` seconds | A `WAITING` session with no heartbeat activity for this long is dropped from the queue. Set high because `netlab up` can take minutes. |
| `_ACTIVE_SESSION_STALE` | `300` seconds | An `ACTIVE` session without a heartbeat for this long is considered stale. The server tears down its lab and promotes the next session. |

The adaptive cleanup cadence reduces resource usage when the server is idle. See [Session Queue](../10-concepts/20-session-queue.md) for how stale sessions are handled.

## Logging Configuration

The server uses Python's `logging.config.dictConfig` with a YAML configuration file. The packaged default is `neops_remote_lab/logging_config.yaml`.

### Default Configuration

The default config defines three formatters and two handlers:

**Formatters:**

| Name | Format | Description |
|------|--------|-------------|
| `standard` | `%(asctime)s [%(levelname)s] %(name)s: %(message)s` | Plain text with timestamps |
| `colored` | Same structure with ANSI color codes | Uses `colorlog.ColoredFormatter` for terminal output. Colors: DEBUG=cyan, INFO=green, WARNING=yellow, ERROR=red, CRITICAL=bold_red |
| `simple` | `[%(levelname)s] %(message)s` | Minimal, no timestamp |

**Handlers:**

| Name | Level | Formatter | Description |
|------|-------|-----------|-------------|
| `console` | `INFO` | `colored` | Standard output handler for normal operation |
| `debug_console` | `DEBUG` | `colored` | Debug output handler, activated when `--debug` or `--log-level DEBUG` is used |

**Logger hierarchy:**

The default config defines dedicated loggers to prevent double-logging:

- `remote-lab-server` -- Main server logger
- `netlab-ordering` -- Netlab operation ordering
- `neops_worker_sdk` -- Worker SDK operations
- `neops_worker_sdk.testing.netlab.connector` -- Netlab connector details
- `uvicorn`, `uvicorn.access`, `uvicorn.error` -- Web server loggers
- `asyncio`, `filelock` -- Third-party loggers (set to `WARNING`)

All loggers have `propagate: false` to avoid duplicate log lines.

### Debug Mode Behavior

When the log level is set to `DEBUG` (via `--debug` or `--log-level DEBUG`), the logging setup function:

1. Updates all configured logger levels to `DEBUG`
2. Switches all loggers from the `console` handler to `debug_console`
3. Updates the root logger level and handler accordingly

This ensures verbose output from all components, including third-party libraries.

### Custom Logging Configuration

Override the default logging by providing a YAML file via `--log-config`:

```bash
neops-remote-lab --log-config /etc/remote-lab/logging.yaml
```

The file must conform to Python's [logging dictionary schema](https://docs.python.org/3/library/logging.config.html#logging-config-dictschema). Example with file output:

```yaml
version: 1
disable_existing_loggers: false

formatters:
  standard:
    format: "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
    datefmt: "%Y-%m-%d %H:%M:%S"

handlers:
  console:
    class: logging.StreamHandler
    level: INFO
    formatter: standard
    stream: ext://sys.stdout

  file:
    class: logging.handlers.RotatingFileHandler
    level: DEBUG
    formatter: standard
    filename: /var/log/remote-lab/server.log
    maxBytes: 10485760  # 10 MB
    backupCount: 5

loggers:
  remote-lab-server:
    level: INFO
    handlers: [console, file]
    propagate: false

root:
  level: WARNING
  handlers: [console]
```

If the custom config file cannot be loaded (file not found, YAML parse error, missing keys), the server falls back to Python's `logging.basicConfig` with the configured log level.
