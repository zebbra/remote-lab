---
title: Run the service
description: Operator-facing reference — install, start the service, run it under systemd, configure it, secure it, look up the REST contract, and debug failures.
tags: [reference, server, operator]
crosslink_defines: []
crosslink_references: []
---

# Run the service

*Install, foreground-launch, healthz — thirty seconds below. Then runbook, knobs, security model, REST contract, and debugging in the pages that follow.*

## 30-second start

!!! info "Have Netlab installed?"
    The launcher refuses to start if `netlab` isn't on `PATH`. If your host is fresh, run [Netlab host setup](../40-deployment/10-netlab-host-setup.md) first — rootless Netlab + Containerlab on Ubuntu in about 20 minutes — then come back here.

Install the CLI in an isolated environment:

=== "uv (recommended)"

    ```bash
    uv tool install neops-remote-lab
    ```

    [`uv tool install`](https://docs.astral.sh/uv/concepts/tools/) drops the CLI in `~/.local/bin` (or `uv tool dir`) inside an isolated environment that uv manages.

=== "pipx"

    ```bash
    pipx install neops-remote-lab
    pipx ensurepath  # only needed once
    ```

    [pipx](https://pipx.pypa.io/) installs into a per-app virtualenv under `~/.local/pipx/venvs/`. After the first install, run `pipx ensurepath` and re-login so `~/.local/bin` is on `PATH`.

=== "pip (last resort)"

    ```bash
    python -m venv ~/.venvs/neops-remote-lab
    ~/.venvs/neops-remote-lab/bin/pip install neops-remote-lab
    ln -s ~/.venvs/neops-remote-lab/bin/neops-remote-lab ~/.local/bin/
    ```

    Manual virtualenv plus a symlink. Prefer `uv tool install` or `pipx` unless you have a hard reason not to.

Start the server in the foreground:

```bash
neops-remote-lab            # binds 0.0.0.0:8000 by default
```

You'll see the lifespan startup sequence — single-instance lock, Netlab CLI check, Uvicorn bind. If `neops-remote-lab` isn't on `PATH`, the install hasn't put it there yet — run `uv tool update-shell`, `pipx ensurepath`, or re-login depending on which installer you used.

In a second terminal, hit the liveness probe:

```bash
curl -s -o /dev/null -w "%{http_code}\n" http://localhost:8000/healthz
```

!!! success "Expected output"
    ```
    204
    ```

`204 No Content` is the liveness signal. Anything else — connection error, `502`, redirect — means the server didn't bind, the port is taken, or your firewall is blocking loopback. Fix transport before continuing; the lab API can't compensate.

!!! danger "No HTTP authentication"
    `neops-remote-lab` ships **without** bearer-token, OAuth, or mTLS authentication. The only access boundary on `/lab/*` is the `X-Session-ID` of an ACTIVE session. **Deploy behind a VPN.** See [Security model](30-security.md) for the full posture.

## What's running, exactly

The server has done four things on startup:

1. Acquired the [single-instance filelock](10-administration.md#single-instance-filelock) under `/tmp/`.
2. Probed for `netlab` on `PATH` — refused to start without it. <!-- trace: neops_remote_lab/__main__.py:206 -->
3. Cleaned up any stale `default` Netlab instance left from a previous crash.
4. Bound Uvicorn on `0.0.0.0:8000`.

It's now waiting for `POST /session`.

## In this section

<div class="grid cards" markdown>

-   :material-account-cog:{ .lg .middle } &nbsp; **[Operator runbook](10-administration.md)**

    ---

    Install via uv/pipx, run under `systemd`, recover from a stale filelock, unstick a wedged lab.

-   :material-tune:{ .lg .middle } &nbsp; **[Server config](20-configuration.md)**

    ---

    CLI flags (`--host`, `--port`, `--debug`, `--log-level`, `--log-config`) and the `NEOPS_NETLAB_STREAM_OUTPUT` env var. Client config lives under [Use from Python](../20-client/30-configuration.md).

-   :material-shield-lock:{ .lg .middle } &nbsp; **[Security model](30-security.md)**

    ---

    What the X-Session-ID gate does and doesn't protect against; the do/don't operational guidance; controls to layer on if you must expose the service.

-   :material-api:{ .lg .middle } &nbsp; **[REST API](40-rest-api.md)**

    ---

    Endpoint-by-endpoint contract: schema, error codes, the `X-Session-ID` matrix, and a cURL example for each.

-   :material-bug:{ .lg .middle } &nbsp; **[Debugging](50-debugging.md)**

    ---

    Symptom/cause/fix table, common HTTP error codes, client and server log patterns, the `/debug/health` endpoint, stale-state recovery. The page to grep when something breaks.

</div>

## What to read next

- **[Architecture](../10-concepts/10-architecture.md)** — why the service is shaped the way it is; the three cooperating components; the one-server-per-host and one-lab-per-host invariants.
- **[Session queue](../10-concepts/20-session-queue.md)** — the FIFO model that the `X-Session-ID` access boundary enforces.
- **[Netlab host setup](../40-deployment/10-netlab-host-setup.md)** — must be complete before the server will start; the launcher exits if `netlab` is not on `PATH`.
- **[Headscale: quick](../40-deployment/20-headscale-quick-setup.md)** — the recommended VPN enclosure for the internal-trust HTTP surface (alternatives in the page's *Other approaches* section).
- **[Wire into CI](../getting-started/40-ci.md)** — wire the service into GitHub Actions, GitLab CI, or Jenkins.
