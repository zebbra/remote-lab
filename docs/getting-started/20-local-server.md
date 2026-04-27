---
title: Local development server
description: Run the Remote Lab Manager locally on Ubuntu — install the prerequisites, start the server on localhost:8000, point your tests at it, and tear down cleanly.
tags: [tutorial, deployment, operator, getting-started]
crosslink_defines: []
crosslink_references: [remote-lab]
---

# Local development server

You don't need a remote VM to develop against `neops-remote-lab`. On Ubuntu
(or any Linux host with rootless Docker), the server runs locally and your
tests point at `http://localhost:8000`. This page is the on-ramp for that
workflow — install once, then `neops-remote-lab` becomes a process you start
when you want a lab and stop when you don't.

If you already have a Remote Lab Manager reachable on a network you control
(a shared zebbra VM, a colleague's host, anything that responds to
`/healthz`), the [Quickstart](10-quickstart.md) is what you want — skip
this page and set `REMOTE_LAB_URL` to the remote URL there.

!!! info "What this page does and doesn't cover"
    **Does cover:** installing the server, the Netlab + Containerlab
    prerequisites, starting the server in the foreground, pointing
    `REMOTE_LAB_URL` at it, tearing down between sessions.

    **Doesn't cover:** running the server under `systemd` (that's
    [Administration → Running as a system service](../30-server/30-administration.md#running-as-a-system-service)),
    enclosing the host in a VPN (that's
    [Headscale VPN](../40-deployment/20-headscale-vpn.md)), or the multi-user
    operator runbook (that's
    [Administration](../30-server/30-administration.md) end-to-end).

---

## Prerequisites

You need three things on the local host:

- **Ubuntu 22.04+** (or another Linux with rootless Docker). macOS works
  for the *client* side of `neops-remote-lab` but not for the *server* —
  Containerlab and Netlab need Linux to spin up real network containers.
- **Python 3.12+** with `pipx` available (`sudo apt install pipx` on
  Ubuntu 24.04+; `pipx ensurepath` to put `~/.local/bin` on `PATH`).
- **Netlab and Containerlab installed rootlessly.** This is non-trivial on
  a fresh machine; the canonical walkthrough is
  [Netlab host setup](../40-deployment/10-netlab-host-setup.md). Run that
  page once, then come back here.

Verify Netlab is reachable before installing the server:

```bash
netlab test clab
```

This boots a tiny FRR topology, confirms Containerlab and the kernel
modules are happy, then tears down. If it fails, fix Netlab first —
`neops-remote-lab` will refuse to start without `netlab` on `PATH`. <!-- trace: neops_remote_lab/__main__.py:206 -->

---

## 1. Install the server

The server ships as the `neops-remote-lab` Python distribution. The
recommended install is [pipx](https://pipx.pypa.io/) — the CLI lands on
`PATH` in its own virtualenv, isolated from your project's environment:

```bash
pipx install neops-remote-lab
```

The package declares a `neops-remote-lab` console script that points at
`neops_remote_lab.__main__:main`, so `pipx install` puts the CLI directly
on your shell's `PATH`. <!-- trace: pyproject.toml:34 -->

Verify:

```bash
which neops-remote-lab
neops-remote-lab --help
```

You should see the install path and the full CLI surface (`--debug`,
`--host`, `--port`, `--log-level`, `--log-config`, `--version`). <!-- trace: neops_remote_lab/__main__.py:149 -->
If you see `command not found`, run `pipx ensurepath` and re-login (or
source your shell's RC file).

---

## 2. Start the server on localhost

For a development session, the simplest run is foreground with debug
logging:

```bash
neops-remote-lab --debug
```

This binds `0.0.0.0:8000`, sets the log level to `DEBUG`, and streams
Netlab subprocess output to the log in real time (the equivalent of
`NEOPS_NETLAB_STREAM_OUTPUT=1`). <!-- trace: neops_remote_lab/__main__.py:163 -->
You'll see the server come up:

```
INFO     | remote-lab-server | Server starting (pid=12345, version=0.x.y)
INFO     | remote-lab-server | Lock acquired at /tmp/neops_remote_lab_server.lock
INFO     | remote-lab-server | netlab CLI found at /home/you/.local/bin/netlab
INFO     | remote-lab-server | Uvicorn running on http://0.0.0.0:8000
```

If you see `Another Remote Lab Manager instance is already running.`
instead, a previous server is still holding the singleton lock — see
[Administration → Stale-lock recovery](../30-server/30-administration.md#stale-lock-recovery).

Confirm the server is reachable from a second terminal:

```bash
curl -fsS http://localhost:8000/healthz && echo OK
```

A `204 No Content` (the body is empty; `&& echo OK` runs because curl
exits 0) is the liveness signal. Anything else means the server didn't
bind, the port is taken, or your firewall is blocking loopback — none of
which the fixture can debug for you.

!!! tip "Bind only to loopback if you don't want others to reach it"
    The default `--host 0.0.0.0` binds on every interface. On a shared
    development machine, prefer `--host 127.0.0.1` so the server is only
    reachable from your own user:
    ```bash
    neops-remote-lab --debug --host 127.0.0.1
    ```
    Tests pointing at `http://localhost:8000` work either way; this just
    closes the open port to anyone else on the network.

---

## 3. Point your tests at localhost

Set `REMOTE_LAB_URL` in the shell where you run pytest:

```bash
export REMOTE_LAB_URL=http://localhost:8000
```

The fixture and `RemoteLabClient` both read this variable; the fixture
fails fast at session setup if it's missing. <!-- trace: neops_remote_lab/testing/fixture.py:34 -->

Drop it into a `.env` if you load one with `python-dotenv` or `direnv`,
so you don't have to remember the export each session.

From here, follow the [Quickstart](10-quickstart.md) from
[step 3 (Write a minimal topology)](10-quickstart.md#3-write-a-minimal-topology)
onward. The test code is identical to the remote case — `pytest` doesn't
know or care whether the server is on the same host or across the
network.

---

## 4. Tear down between sessions

When you're done with a development session, stop the server with `Ctrl+C`
in the terminal where it's running. The shutdown sequence:

1. SIGINT triggers the server's signal handler, which sets
   `_SHUTDOWN_EVENT`.
2. The lifespan context manager cancels the cleanup loop, deletes any
   tracked sessions, and runs a final `LabManager.cleanup` to tear down
   the running lab.
3. The `atexit` hook fires as the interpreter exits, as a last-resort
   cleanup if anything in step 2 was missed.
4. The singleton filelock is released.

Confirm there's nothing lingering:

```bash
docker ps                 # no clab-* containers
ls /tmp/neops_remote_lab_server.*  # no lockfile or metadata
netlab status default     # "No active lab instance"
```

If a container, lockfile, or netlab default instance is still alive, the
server didn't tear down cleanly — see
[Administration → Forced cleanup of a stuck lab](../30-server/30-administration.md#forced-cleanup-of-a-stuck-lab).

---

## When to graduate to a remote server

Local-dev is the right shape for: writing tests, debugging failures
quickly, exploring topology shapes. It's the wrong shape when:

- **More than one developer or CI job needs the lab.** The one-server-
  per-host invariant means a second developer cannot run their own server
  on your machine; a shared VM (with [Headscale VPN](../40-deployment/20-headscale-vpn.md)
  in front of it) is the multi-user shape.
- **You need the lab to outlive your shell session.** Local-dev assumes
  you stop the server when you stop working. A long-lived service belongs
  under [systemd on a dedicated host](../30-server/30-administration.md#running-as-a-system-service).
- **Test runs are heavy enough to interfere with your laptop.** Containerlab
  is greedy with CPU and RAM during `netlab up`; offloading to a
  dedicated VM keeps your editor responsive.

When you cross any of these thresholds, the
[Deployment](../40-deployment/index.md) section walks through standing up
a shared host. The test code and `REMOTE_LAB_URL` switch is the only
change on the consumer side.

---

## Where to go next

- **[Quickstart](10-quickstart.md)** — write your first test against the
  server you just started.
- **[Architecture](../10-concepts/10-architecture.md)** — the high-level
  picture of how the local server is structured (it's the same server you
  would run on a shared host; only the network topology differs).
- **[Administration](../30-server/30-administration.md)** — the operator
  reference, including stale-lock recovery, the security posture you sign
  up for, and the systemd unit if you want the server to come back after
  reboot.
- **[Headscale VPN](../40-deployment/20-headscale-vpn.md)** — when local
  is no longer enough, the recommended VPN enclosure for a shared host.
