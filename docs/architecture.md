---
title: Architecture
description: How neops-remote-lab composes a FastAPI server, a LabManager singleton, and a pytest plugin to give tests exclusive access to Netlab topologies.
tags: [concept, server, testing, lifecycle]
crosslink_defines: [remote-lab]
crosslink_references: []
---

# Architecture

A Netlab topology can only run once per host. When several developers or CI jobs
want to run integration tests against the same hardware-free network, they need
a queue, a heartbeat, and someone to tear the lab down when the last test walks
away. `neops-remote-lab` is that queue.

> **Why a server?** Netlab is a host-local tool. Running it inside each test
> runner would mean one lab per runner — expensive, and it collides with the
> one-lab-per-host rule anyway. A small HTTP service in front of Netlab lets
> many clients share one lab host safely.

## Three components, one process per host

`neops-remote-lab` ships three pieces that cooperate across the network:

| Component | Runs on | Role |
|---|---|---|
| FastAPI server (`neops_remote_lab.server`) | The lab host | Accepts sessions, queues them FIFO, invokes Netlab for the active session. |
| `LabManager` singleton | In the server process | Tracks the one running lab; enforces the one-lab-per-host rule; reference-counts reuse. |
| `RemoteLabClient` + `remote_lab_fixture` | Your CI / dev machine | Creates a session, heartbeats it, uploads a topology, yields devices to your test, releases on teardown. |

```mermaid
sequenceDiagram
    participant Test as pytest (remote_lab_fixture)
    participant Client as RemoteLabClient
    participant Server as FastAPI server
    participant Manager as LabManager
    participant Netlab

    Test->>Client: acquire topology
    Client->>Server: POST /session
    Server-->>Client: session_id (WAITING)
    Client->>Server: GET /session/{id} (poll until ACTIVE)
    Client->>Server: POST /lab (multipart: topology + extra_files)
    Server->>Manager: try_acquire(topo, reuse=True)
    Manager->>Netlab: netlab up topology.yml
    Netlab-->>Manager: nodes
    Manager-->>Server: devices
    Server-->>Client: 200 devices
    loop every <300s
        Client->>Server: POST /session/heartbeat
    end
    Test->>Client: release()
    Client->>Server: POST /lab/release
    Server->>Manager: release() ref--
    Client->>Server: DELETE /session/{id}
```

## Request flow: session, then lab

Every `/lab/*` call is gated by two things: a valid `X-Session-ID` header and
that session being the head of the FIFO queue. The same gate applies to
`/session/heartbeat`.

<!-- trace: neops_remote_lab/server.py:390 -->
Non-active sessions receive `423 Locked`. The server never shortcuts the queue;
the only way to skip ahead is to wait for the head to release or time out.
See [session-queue.md](session-queue.md) for the promotion and timeout rules.

## The one-server-per-host guard

<!-- trace: neops_remote_lab/__main__.py:104 -->
At startup the entrypoint acquires a non-blocking `FileLock` under the system
temp directory. If a second instance tries to start on the same host, the lock
fails immediately and the new process logs the owner's PID, user, host, bind
address, and the command that started it — then exits with status 1.

!!! warning "Stale locks after a crash"
    If a previous server crashed without running its cleanup, the lock file may
    remain. The entrypoint detects this by reading the companion metadata file
    and probing whether the recorded PID is still alive; when the PID is gone
    it clears the stale metadata and proceeds. If both are stuck (live PID for a
    process that is actually hung), kill the PID manually. See
    [administration.md](administration.md) once it lands.

## The one-lab-per-host guard

<!-- trace: neops_remote_lab/netlab/lab_manager.py:43 -->
Netlab itself can only manage one topology at a time per host. `LabManager` is
a classmethod-only singleton; its state lives on the class, and a
system-wide `FileLock` under the temp directory serialises access across any
additional Python processes (e.g. local tests running alongside the server).

> **Why both?** The singleton prevents two async tasks in the server from
> racing. The `FileLock` prevents a developer from accidentally running a local
> `netlab` process in parallel with the server on the same host.

## The async discipline

Netlab commands take minutes: they build containers, boot routers, and install
configurations. If the FastAPI event loop blocked on them, every other client
polling `GET /session/{id}` would stall.

<!-- trace: neops_remote_lab/server.py:163 -->
The server funnels every Netlab-bound operation through `_run_blocking`, which
dispatches the call to the default `asyncio` thread-pool executor. Only
heavyweight operations (`LabManager.try_acquire`, `LabManager.cleanup`) go
through this path; lightweight metadata reads like `LabManager.status()` stay
synchronous to avoid thread-hop overhead.

!!! danger "Do not add async code to the atexit teardown"
    `LabManager` registers a synchronous `cleanup` on `atexit`. If you put
    anything that awaits an event loop there, the interpreter deadlocks at
    shutdown because the loop is already closed. Details in
    [lab-lifecycle.md](lab-lifecycle.md).

## How Netlab is invoked

<!-- trace: neops_remote_lab/netlab/connector.py:85 -->
There is exactly one path to the Netlab CLI: `run_netlab` in
`neops_remote_lab.netlab.connector`. It builds the argv as
`["netlab", *args]`, runs the subprocess, and streams or captures stdout
depending on the `NEOPS_NETLAB_STREAM_OUTPUT` env var. Never shell out to
`netlab` from anywhere else in the codebase — the concentrator gives us
uniform logging, error handling, and the `expected_failure` flag for silent
cleanup attempts.

## Ecosystem position

```mermaid
flowchart LR
    subgraph consumer ["Consumer repositories (tests)"]
        worker_tests["neops-worker-sdk-py tests"]
        fb_tests["function-block test suites"]
    end
    subgraph fixture ["remote_lab_fixture factory"]
        fx[remote_lab_fixture]
    end
    subgraph client ["neops-remote-lab client"]
        rlc[RemoteLabClient]
    end
    subgraph server ["neops-remote-lab server (one per host)"]
        srv[FastAPI]
        mgr[LabManager]
    end
    subgraph host ["Lab host"]
        nl[Netlab CLI]
        clab[Containerlab / libvirt]
    end
    worker_tests --> fx
    fb_tests --> fx
    fx --> rlc
    rlc -- "HTTP + X-Session-ID" --> srv
    srv --> mgr
    mgr -- "run_netlab()" --> nl
    nl --> clab
```

`remote_lab_fixture` is the **stable public API**. Consumer repositories —
notably `neops-worker-sdk-py` — import it directly and treat its call signature
as a contract. Changing its arguments is a breaking change. The REST surface
and `RemoteLabClient` are lower-level and may evolve more freely, but in
practice the fixture uses them both so any incompatible change ripples.

!!! info "Authentication is not implemented"
    The `X-Session-ID` header is the only access boundary on `/lab/*` and
    `/session/heartbeat`. Bearer-token scaffolding exists in `client.py` but is
    commented out. Deploy this service on an internal-trust network only — the
    Headscale/Tailscale setup under [headscale_headplane.md](headscale_headplane.md)
    is the expected enclosure.

## Where to go next

- [session-queue.md](session-queue.md) — FIFO promotion, heartbeats, and the
  stale-session sweep that keeps a crashed client from blocking the queue.
- [lab-lifecycle.md](lab-lifecycle.md) — SHA-based topology identity, reference
  counting, the `try_acquire` vs `acquire` distinction, and `atexit` teardown.
- [topology-format.md](topology-format.md) — the YAML shape and the `.yml`
  extension trap.
