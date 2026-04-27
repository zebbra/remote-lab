---
title: Start it
description: Run the Remote Lab Manager in the foreground and confirm it answers — the 30-second sanity check before anything else on this section.
tags: [tutorial, operator]
crosslink_defines: []
crosslink_references: []
---

# Start it

*Thirty seconds, two commands. Run the server in the foreground and confirm the liveness probe answers — every other page in this section assumes you've done this once.*

!!! danger "No HTTP authentication"
    `neops-remote-lab` ships **without** bearer-token, OAuth, or mTLS
    authentication. The only access boundary on `/lab/*` is the
    `X-Session-ID` of an ACTIVE session. **Deploy behind a VPN.** See
    [Security model](30-security.md) for the full posture.

## 1. Start it in the foreground

```bash
neops-remote-lab            # binds 0.0.0.0:8000 by default
```

You'll see the lifespan startup sequence — single-instance lock, Netlab CLI check, Uvicorn bind. If `neops-remote-lab` isn't on `PATH`, you haven't installed it yet — see the [Operator runbook](10-administration.md).

!!! tip "Bind to a specific interface"
    On a multi-homed host where you don't want the service reachable on every NIC, pass `--host`:

    ```bash
    neops-remote-lab --host 10.0.0.2 --port 8000
    ```

## 2. Confirm the liveness probe

In a second terminal:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/healthz
```

!!! success "Expected output"
    ```
    204
    ```

`204 No Content` is the liveness signal. Anything else — a connection error, a `502`, a redirect — means the server didn't bind, the port is taken, or your firewall is blocking loopback. Fix transport before continuing; the lab API can't compensate.

## What's running, exactly

The server has done four things:

1. Acquired the [single-instance filelock](10-administration.md#single-instance-filelock) under `/tmp/`.
2. Probed for `netlab` on `PATH` — refused to start without it. <!-- trace: neops_remote_lab/__main__.py:206 -->
3. Cleaned up any stale `default` Netlab instance left from a previous crash.
4. Bound Uvicorn on `0.0.0.0:8000`.

It's now waiting for `POST /session`.

## Where to go next

<div class="grid cards" markdown>

-   :material-account-cog:{ .lg .middle } &nbsp; **[Operator runbook](10-administration.md)**

    ---

    Install via uv/pipx, run under `systemd`, recover from a stale lock, unstick a wedged lab.

-   :material-tune:{ .lg .middle } &nbsp; **[Server config](20-configuration.md)**

    ---

    CLI flags (`--host`, `--port`, `--debug`, `--log-level`, `--log-config`) and the `NEOPS_NETLAB_STREAM_OUTPUT` env var.

-   :material-shield-lock:{ .lg .middle } &nbsp; **[Security model](30-security.md)**

    ---

    What the X-Session-ID gate does — and doesn't — protect against; the do/don't operational guidance; controls to layer on if you must expose the service.

-   :material-bug:{ .lg .middle } &nbsp; **[Debugging](50-debugging.md)**

    ---

    Symptom/cause/fix table; HTTP error codes; client and server log patterns; stale-state recovery.

</div>
