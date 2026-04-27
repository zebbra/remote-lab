---
title: Glossary
description: One-line definitions for every term the docs use, grouped by domain and cross-linked to the page where the concept lives.
tags: [reference, appendix]
crosslink_defines: []
crosslink_references: []
---

# Glossary

One-line definitions, grouped by domain. Each entry links to the in-depth page where the concept lives. For peer-project terminology (Function Block, Worker, Workflow, Provider, Blackboard, Context), see [How Remote Lab fits with neops](neops-ecosystem.md).

---

## Sessions and queueing

**Session**
:   A logical reservation in the server's FIFO queue, identified by a UUID. Either `WAITING` (queued) or `ACTIVE` (head of queue). See [Session queue](../10-concepts/20-session-queue.md).

<a id="session-queue"></a>**Session queue**
:   Server-side FIFO list that decides who drives the lab next; promotion is first-come, first-served. See [Session queue → Promotion order](../10-concepts/20-session-queue.md#promotion-order).

**Heartbeat**
:   `POST /session/heartbeat` — refreshes `last_seen_at` so the server does not evict the session as stale. See [Session queue → The heartbeat](../10-concepts/20-session-queue.md#the-heartbeat).

**`X-Session-ID`**
:   The HTTP header that gates `/lab/*`; **the only access boundary on the lab surface**. See [REST API → The X-Session-ID contract](../30-server/10-rest-api.md#the-x-session-id-contract).

---

## Labs and topologies

**Lab**
:   A running Netlab topology on the host — at most one at a time. See [Lab lifecycle](../10-concepts/30-lab-lifecycle.md).

**Topology**
:   A Netlab YAML file (`.yml`) declaring nodes, links, modules, and provider. See [Topology format](../10-concepts/40-topology-format.md).

**Topology identity**
:   The SHA-256 of the topology file's bytes — **not** the filename. See [Lab lifecycle → Topology identity](../10-concepts/30-lab-lifecycle.md#topology-identity-is-content-not-filename).

**Reference count**
:   Counter on the running lab; `reuse=true` increments, `release` decrements, hitting zero leaves the lab idle (not torn down). See [Lab lifecycle → Reuse](../10-concepts/30-lab-lifecycle.md#reuse-the-refcount-increments).

**Lab reuse**
:   Opt-in (`reuse=true` / `reuse_lab=True`) sharing of a running lab across sessions whose topology content hash matches. See [Lab lifecycle → Reuse](../10-concepts/30-lab-lifecycle.md#reuse-the-refcount-increments).

**One-lab rule**
:   Netlab's "only one topology per host" constraint; the queue exists because of it. See [Invariants → One lab per host](../50-contributing/20-invariants.md#one-lab-per-host).

---

## Locking and concurrency

**`LabManager`**
:   Class-only singleton (no instances) that owns the running lab and enforces one-lab-per-host. See [LabManager singleton](../50-contributing/40-internals-lab-manager.md).

**`GLOBAL_LOCK`**
:   `filelock.FileLock` at `<tempdir>/netlab_pytest.lock` — serializes lab operations across processes. See [Invariants → One lab per host](../50-contributing/20-invariants.md#one-lab-per-host).

**Single-instance filelock**
:   Separate `FileLock` in `__main__.py` that prevents two server processes on one host. See [Invariants → One server instance per host](../50-contributing/20-invariants.md#one-server-instance-per-host).

**`try_acquire` vs `acquire`**
:   `try_acquire` is non-blocking (server uses this); `acquire` polls forever (local fixtures only). Mixing them deadlocks the event loop. See [LabManager → `try_acquire` vs `acquire`](../50-contributing/40-internals-lab-manager.md#try_acquire-vs-acquire).

**`atexit` teardown**
:   Synchronous, silent cleanup hook that tears down any live lab on interpreter exit. Never add async code. See [atexit + lifespan](../50-contributing/50-internals-atexit.md#atexit-teardown).

---

## Data models

**`*Dto` suffix**
:   Every Pydantic request/response model ends in `Dto`; code review enforces it. See [Invariants → `*Dto` suffix](../50-contributing/20-invariants.md#dto-suffix).

<a id="deviceinfodto"></a>**`DeviceInfoDto`**
:   `{name, raw}` — one entry per device in a running lab. Returned by `POST /lab` and `GET /lab/devices`.

**`AcquireResponseDto`**
:   `{reused, devices}` — response body of `POST /lab`.

**`SessionStatusResponseDto`**
:   `{status, position}` — response body of `GET /session/{id}`.

**`CreateSessionResponseDto`**
:   `{session_id, position}` — response body of `POST /session`.

**`LabStatusDto`**
:   Response body of `GET /lab` — running topology and current device list.

---

## Testing & client

**`remote_lab_fixture`**
:   The factory creating a function-scoped pytest fixture bound to a topology — **the stable public API of this project**. See [Pytest fixtures](../20-client/10-pytest-fixtures.md).

**`remote_lab_client`**
:   Session-scoped pytest fixture wrapping a single `RemoteLabClient`; fails fast if `REMOTE_LAB_URL` is unset. See [Python client](../20-client/20-python-client.md).

**Fixture**
:   A pytest setup/teardown hook injected into a test by parameter name. See [pytest docs](https://docs.pytest.org/en/stable/explanation/fixtures.html).

**Fixture scope**
:   How long pytest keeps a fixture alive (`function`, `class`, `module`, `package`, `session`). See [pytest docs](https://docs.pytest.org/en/stable/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-or-session).

**`conftest.py`**
:   pytest-discovered file whose contents auto-load for tests in that directory tree without an `import`. See [pytest docs](https://docs.pytest.org/en/stable/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files).

**`pytest11` entry point**
:   `[project.entry-points.pytest11]` — how pytest discovers installed plugins. `neops-remote-lab` registers itself this way. See [pytest docs](https://docs.pytest.org/en/stable/how-to/writing_plugins.html#making-your-plugin-installable-by-others).

**Fixture rank**
:   Auto-incremented integer per `remote_lab_fixture`; the ordering plugin uses ranks to keep tests against the same lab contiguous. See [Pytest fixtures → Test execution ordering](../20-client/10-pytest-fixtures.md#test-execution-ordering).

---

## Upstream tools

**[Netlab](https://netlab.tools/)**
:   The lab orchestrator this service wraps. Used via `neops_remote_lab.netlab.connector.run_netlab` only. See [Netlab host setup](../40-deployment/10-netlab-host-setup.md).

**[Containerlab](https://containerlab.dev/)**
:   Netlab's default provider (`provider: clab`); pulls vendor NOS containers and wires them.

**[FRR](https://frrouting.org/)**
:   Open-source software router; the default `device:` in most topologies. See [Vendor setup → FRR](../40-deployment/40-vendor-setup.md#frrouting-device-frr).

**[Nokia SR Linux](https://learn.srlinux.dev/)**
:   Container-native vendor NOS, free under Nokia EULA. See [Vendor setup → Nokia SR Linux](../40-deployment/40-vendor-setup.md#nokia-sr-linux-device-srlinux).

**[Cisco IOL](https://netlab.tools/platforms/cisco_iol/)**
:   IOS-on-Linux, license required. See [Vendor setup → Cisco IOL](../40-deployment/40-vendor-setup.md#cisco-iol-device-cisco_iol-license-required).

**[Headscale](https://headscale.net/)**
:   Self-hosted Tailscale control plane; the recommended enclosure for the no-auth lab service. See [Headscale VPN](../40-deployment/20-headscale-quick-setup.md).

**[Headplane](https://github.com/tale/headplane)**
:   Web UI for Headscale.

**[Tailscale](https://tailscale.com/kb/)**
:   The mesh VPN whose protocol Headscale implements.

**Subnet router**
:   A Tailscale node advertising lab subnet routes to the rest of the mesh — typically the lab host itself. See [Headscale VPN → Quick setup](../40-deployment/20-headscale-quick-setup.md#register-the-lab-host-as-a-subnet-router).

---

## Peer-project terminology

Peer-project terminology (Function Block, Worker, Workflow, Provider, Blackboard, Context, etc.) — see [How Remote Lab fits with neops](neops-ecosystem.md).
