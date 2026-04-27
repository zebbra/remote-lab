---
title: Glossary
description: Every term the docs use — sessions, labs, locking, data models, testing, networking — defined and cross-linked to the in-depth page where the concept lives.
tags: [reference, appendix]
crosslink_defines: []
crosslink_references: []
---

# Glossary

Terms are grouped by domain. Each entry points at the in-depth page where
the concept is fully explained, and at the upstream tool's authoritative
documentation when there is one. The last section bridges terminology with
neighbouring projects in the neops ecosystem so an External API user
arriving from a peer repo can tell where their mental model transfers and
where it does not.

---

## Sessions and queueing

The Remote Lab Manager serializes access to the lab host through a FIFO
session queue. The terms in this section describe that queue and the
identity, lifecycle, and access boundary that go with each session.
Definitions are cross-linked to [Session queue](../10-concepts/20-session-queue.md)
and [REST API](../30-server/10-rest-api.md).

<a id="session"></a>
Session
:   A logical reservation in the server's FIFO queue, identified by a
    UUID returned from `POST /session`. A session is in exactly one state
    at a time — `WAITING` (behind one or more sessions in the queue) or
    `ACTIVE` (at the head of the queue) — and is removed when the client
    `DELETE`s it or when the server evicts it for staleness. See
    [Session queue → The state machine](../10-concepts/20-session-queue.md#the-state-machine).

<a id="session-queue"></a>
Session queue
:   The server-side FIFO list that decides who drives the lab next. The
    head is the `ACTIVE` session (if any); the rest are `WAITING` in
    insertion order. Promotion is first-come, first-served — there is no
    priority scheme. See
    [Session queue → Promotion order](../10-concepts/20-session-queue.md#promotion-order).

<a id="active-session"></a>
Active session
:   The session at position 0 in the queue. Only the active session may
    call `/lab/*` endpoints. Non-active sessions receive `423 Locked`. See
    [Session queue → The access boundary](../10-concepts/20-session-queue.md#the-access-boundary).

<a id="waiting-session"></a>
Waiting session
:   Any session behind position 0. The client polls `GET /session/{id}` to
    watch its position; the poll itself updates `last_seen_at`, which is
    why a polling waiter does not go stale. Waiting sessions are evicted
    after 600 seconds of no activity. See
    [Session queue → Stale-session eviction](../10-concepts/20-session-queue.md#stale-session-eviction).

<a id="heartbeat"></a>
Heartbeat
:   A `POST /session/heartbeat` call (with `X-Session-ID`) that updates
    the session's `last_seen_at` timestamp and returns `204`. It works for
    both `WAITING` and `ACTIVE` sessions — the state gate sits on
    `/lab/*`, not on heartbeat. An active session goes stale after
    300 seconds without a heartbeat or other activity; the pytest fixture
    and `RemoteLabClient` do this automatically, but a non-Python client
    has to do it by hand. See
    [Session queue → The heartbeat](../10-concepts/20-session-queue.md#the-heartbeat).
    For the contrast with the workflow-engine's heartbeat, see
    [Heartbeat (peer-project contrast)](#heartbeat-peer) below.

<a id="x-session-id"></a>
X-Session-ID
:   The HTTP header that carries session identity on every `/lab/*`
    request and on `/session/heartbeat`. It is **the only access boundary**
    on `/lab/*` — there is no Bearer token, no mTLS, no tenant header.
    Treat the service as internal-trust. See
    [REST API → The X-Session-ID contract](../30-server/10-rest-api.md#the-x-session-id-contract)
    and [Administration → Security posture](../30-server/30-administration.md#security-posture).

<a id="fifo-promotion"></a>
FIFO promotion
:   The rule by which the queue head moves forward: when the active
    session releases (or is evicted), the next waiting session is
    promoted to active. There is no reordering — a session three places
    back staying or leaving does not change anyone else's position. See
    [Session queue → Promotion order](../10-concepts/20-session-queue.md#promotion-order).

---

## Labs and topologies

A lab is a running Netlab topology on the host. The terms below describe
how the server identifies a topology, when it reuses the running lab, and
the constraints that fall out of Netlab's one-lab-per-host rule.
Cross-linked to [Lab lifecycle](../10-concepts/30-lab-lifecycle.md) and
[Topology format](../10-concepts/40-topology-format.md).

<a id="lab"></a>
Lab
:   The set of containers and links that Netlab brings up from a topology
    file. A lab is started by uploading a topology to `POST /lab` and
    torn down on release (when the reference count drops and a different
    topology is requested), `DELETE /lab`, session eviction, or
    interpreter exit. See [Lab lifecycle](../10-concepts/30-lab-lifecycle.md).

<a id="topology"></a>
Topology
:   A Netlab YAML file (`.yml`) that declares the network: `provider`,
    nodes, links, modules, and per-device overrides. Uploaded to the
    server as `multipart/form-data`. The dialect is Netlab's
    ([upstream reference](https://netlab.tools/topology-overview/)); the
    `.yml` extension and the `extra_files` upload contract are enforced
    by *this* server. See
    [Topology format](../10-concepts/40-topology-format.md).

<a id="topology-identity"></a>
Topology identity (content hash)
:   The SHA-256 digest of the topology file's bytes. **Two files with
    different names but identical content are the same topology.** Edit
    one byte and it is a new topology. This drives the reuse decision in
    `LabManager.try_acquire()`. Most systems key on filename — this one
    does not. See
    [Lab lifecycle → Topology identity is content, not filename](../10-concepts/30-lab-lifecycle.md#topology-identity-is-content-not-filename).

<a id="reference-count"></a>
Reference count
:   The integer in `LabManager._handle.ref` that tracks how many sessions
    currently hold the running lab. Incremented on each `try_acquire`
    with `reuse=True`; decremented on `release`. When it drops to zero
    the lab becomes idle but stays running until a different topology is
    requested or cleanup fires. See
    [Lab lifecycle → Reuse: the refcount increments](../10-concepts/30-lab-lifecycle.md#reuse-the-refcount-increments).

<a id="lab-reuse"></a>
Lab reuse
:   The opt-in behaviour (`reuse=true` on `POST /lab`, or `reuse_lab=True`
    on a `remote_lab_fixture`) that lets multiple sessions share one
    running lab. Reuse only succeeds when the topology content hash
    matches the running lab's. A lab boot can take minutes; reuse turns
    it into a one-time cost per test session. See
    [Lab lifecycle → Reuse](../10-concepts/30-lab-lifecycle.md#reuse-the-refcount-increments).

<a id="one-lab-rule"></a>
One-lab rule
:   The Netlab constraint that only one topology may run per host at any
    time. Enforced process-wide by `LabManager` (a class-only state
    container — never instantiated) and cross-process by [`GLOBAL_LOCK`](#global-lock).
    The session queue is the user-facing consequence of this rule. See
    [Invariants & internals → One lab per host](../50-contributing/20-invariants.md#one-lab-per-host).

<a id="yml-extension-trap"></a>
`.yml` extension trap
:   `LabManager.prepare_workdir` only accepts files whose suffix is
    exactly `.yml` (lowercase). The HTTP layer is more permissive and
    accepts `.yaml` too — so a `.yaml` upload passes the HTTP check, the
    session is promoted to `ACTIVE`, and *then* `LabManager` raises. The
    queue slot is wasted. Canonicalise topology filenames to `.yml`
    everywhere. See
    [Lab lifecycle → The `.yml` extension trap](../10-concepts/30-lab-lifecycle.md#the-yml-extension-trap)
    and [Invariants & internals → `.yml` extension is required](../50-contributing/20-invariants.md#yml-extension-is-required-by-labmanager).

---

## Locking and concurrency

Two layers of locking enforce one server per host and one lab per host —
an in-process singleton class plus cross-process file locks. The
`atexit` teardown is the last safety net. Cross-linked to
[Invariants & internals](../50-contributing/20-invariants.md).

<a id="labmanager"></a>
`LabManager`
:   The class in `neops_remote_lab/netlab/lab_manager.py` that owns the
    running lab. It is a class-only singleton: every method is a
    `classmethod` and there are no instances. State (current topology,
    content hash, reference-counted handle) lives on the class. The
    pattern is unusual but deliberate — there is at most one lab per
    host, so there is at most one set of state. See
    [Invariants & internals → The `LabManager` singleton](../50-contributing/20-invariants.md#the-labmanager-singleton).

<a id="global-lock"></a>
`GLOBAL_LOCK`
:   A `filelock.FileLock` at `<tempdir>/netlab_pytest.lock` that
    serializes lab operations across multiple OS processes. Any code path
    that starts, reuses, or tears down a lab acquires this lock. It
    catches a developer running `netlab` by hand alongside the server.
    See [Invariants & internals → One lab per host](../50-contributing/20-invariants.md#one-lab-per-host).

<a id="single-instance-filelock"></a>
Single-instance filelock
:   A separate `FileLock` taken non-blockingly in `__main__.py` at
    `<tempdir>/neops_remote_lab_server.lock`. It prevents two
    `neops-remote-lab` server processes from starting on the same host;
    the loser logs the running owner's pid/user/host and exits with
    status 1. See
    [Invariants & internals → One server instance per host](../50-contributing/20-invariants.md#one-server-instance-per-host)
    and [Administration → Stale-lock recovery](../30-server/30-administration.md#stale-lock-recovery).

<a id="try-acquire-vs-acquire"></a>
`try_acquire` vs `acquire`
:   Two `LabManager` methods with almost identical signatures and
    opposite blocking behaviour. **`try_acquire`** is non-blocking and
    returns `None` when the lab is busy with an incompatible request — the
    server uses this from inside an async handler. **`acquire`** is a
    polling wrapper that sleeps 2 s and retries forever — local in-process
    fixtures use this when blocking is the point. Calling `acquire` from
    inside the event loop is one of the easier ways to wedge the test
    suite. See
    [Invariants & internals → `try_acquire` vs `acquire`](../50-contributing/20-invariants.md#try_acquire-vs-acquire).

<a id="atexit-teardown"></a>
`atexit` teardown
:   `LabManager` registers a synchronous, silent cleanup with
    `atexit.register` at module import time. It runs on normal exit, on
    `SIGTERM`, and after a pytest crash, and tears down any lab still up.
    Two non-obvious choices: it runs with `silent=True` (logging handlers
    have already closed their streams by exit time) and it is
    deliberately synchronous (no event loop is running at `atexit`, so
    `await` would deadlock the interpreter). Never add async code to this
    path. See
    [Invariants & internals → atexit teardown](../50-contributing/20-invariants.md#atexit-teardown).

---

## Data models

Pydantic 2 request/response models on the HTTP surface, all suffixed
`Dto`. The suffix is load-bearing: it lets a reader scan a file and
distinguish wire-format models from internal types at a glance, and code
review will reject a model without it. Cross-linked to
[REST API](../30-server/10-rest-api.md) and
[Invariants & internals → `*Dto` suffix](../50-contributing/20-invariants.md#dto-suffix).

<a id="dto-suffix"></a>
`*Dto` suffix convention
:   Every request and response model in `neops_remote_lab.models.*` ends
    in `Dto`. Mixing wire-format models with internal types is a recipe
    for accidentally serialising internal state to the HTTP surface; the
    suffix prevents that. See
    [Invariants & internals → `*Dto` suffix](../50-contributing/20-invariants.md#dto-suffix).

<a id="deviceinfodto"></a>
`DeviceInfoDto`
:   The Pydantic model that represents one device in a running lab.
    Fields: `name` (the Netlab node name) and `raw` (the full
    `netlab inspect` output as a dict, including management IPs and
    connection details). Returned as a list by `POST /lab` and
    `GET /lab/devices`. See
    [REST API → `POST /lab`](../30-server/10-rest-api.md#post-lab-upload-topology-and-acquire-the-lab).

<a id="acquireresponsedto"></a>
`AcquireResponseDto`
:   The response body from `POST /lab`. Two fields: `reused` (bool —
    `true` if the upload incremented the refcount on a running lab,
    `false` if Netlab booted a fresh topology) and `devices`
    (`list[DeviceInfoDto]`). See
    [REST API → `POST /lab`](../30-server/10-rest-api.md#post-lab-upload-topology-and-acquire-the-lab).

<a id="sessionstatusresponsedto"></a>
`SessionStatusResponseDto`
:   The response from `GET /session/{id}`. Reports `status`
    (`"waiting"` / `"active"`) and `position` (0 means active, ≥1 means
    waiting). The poll itself refreshes `last_seen_at`. See
    [REST API → `GET /session/{session_id}`](../30-server/10-rest-api.md#get-sessionsession_id-poll-session-status).

<a id="createsessionresponsedto"></a>
`CreateSessionResponseDto`
:   The response from `POST /session`. Fields: `session_id` (UUID) and
    `position` (0 means already active). See
    [REST API → `POST /session`](../30-server/10-rest-api.md#post-session-create-a-session).

<a id="labstatusdto"></a>
`LabStatusDto`
:   The response from `GET /lab`. Reports whether a lab is running,
    which topology, and the current device list. See
    [REST API](../30-server/10-rest-api.md).

---

## Testing & client

The Python side: the pytest fixture factory, the session-scoped client
fixture, and the entry-point that registers them. Cross-linked to
[Pytest fixtures](../20-client/10-pytest-fixtures.md) and
[Python client](../20-client/20-python-client.md).

<a id="remote-lab-fixture"></a>
`remote_lab_fixture`
:   The factory function that creates a function-scoped pytest fixture
    bound to a topology file. **The stable public API of this project** —
    `neops-worker-sdk-py` imports it directly and its signature is part
    of that contract. Arguments: `topology` (path), `name` (override),
    `reuse_lab` (bool). Each call produces a real `pytest.fixture`. See
    [Pytest fixtures](../20-client/10-pytest-fixtures.md).

<a id="remote-lab-client"></a>
`remote_lab_client`
:   A session-scoped pytest fixture that creates and manages a single
    `RemoteLabClient` instance for the entire pytest run. Fails fast at
    test setup with `RuntimeError` if `REMOTE_LAB_URL` is not set. See
    [Python client](../20-client/20-python-client.md).

<a id="fixture"></a>
Fixture
:   A pytest setup/teardown hook that produces a value (or `yield`s one)
    and injects it into a test by parameter name. See the upstream
    [pytest fixtures explanation](https://docs.pytest.org/en/stable/explanation/fixtures.html).

<a id="fixture-scope"></a>
Fixture scope
:   How long pytest keeps a fixture's value alive: `function` (per test,
    default), `class`, `module`, `package`, or `session` (per pytest
    run). Remote Lab uses `session` for `remote_lab_client` and
    `function` for fixtures created by `remote_lab_fixture`. See the
    [pytest scope reference](https://docs.pytest.org/en/stable/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-or-session).

<a id="conftest-py"></a>
`conftest.py`
:   A pytest-discovered file in a test directory whose contents
    (fixtures, hooks, plugins) are auto-loaded for every test in that
    directory tree without an `import`. Where you typically declare your
    `remote_lab_fixture(...)` calls. See the
    [pytest conftest reference](https://docs.pytest.org/en/stable/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files).

<a id="pytest11-entry-point"></a>
`pytest11` entry point
:   The Python package metadata key
    (`[project.entry-points.pytest11]` in `pyproject.toml`) that pytest
    scans on startup to discover plugins. `neops-remote-lab` registers
    itself this way, so the fixture factory and the test-ordering plugin
    are available as soon as the package is installed — no `conftest.py`
    boilerplate needed. See the
    [pytest plugin discovery reference](https://docs.pytest.org/en/stable/how-to/writing_plugins.html#making-your-plugin-installable-by-others).

<a id="fixture-rank"></a>
Fixture rank
:   An auto-incremented integer assigned to each `remote_lab_fixture` in
    declaration order. The collection-time ordering plugin uses ranks to
    group tests by topology so that all tests sharing a lab run
    consecutively, minimising teardown/rebuild cycles. See
    [Pytest fixtures → Test execution ordering](../20-client/10-pytest-fixtures.md#test-execution-ordering).

---

## Networking & infrastructure

The upstream tools `neops-remote-lab` wraps or interoperates with. Each
entry links to the authoritative reference for that tool — the docs on
this site explain how Remote Lab uses the tool, not the tool itself.

<a id="netlab"></a>
[Netlab](https://netlab.tools/)
:   The network lab orchestrator (`netlab` CLI, PyPI package
    `networklab`) that Remote Lab wraps. Netlab takes a topology YAML,
    coordinates a virtualization provider (Containerlab by default,
    libvirt optionally), and configures the resulting devices via
    Ansible. Remote Lab invokes Netlab through a single helper —
    `neops_remote_lab.netlab.connector.run_netlab` — and never shells out
    to `netlab` directly. See
    [Netlab host setup](../40-deployment/10-netlab-host-setup.md) and
    the upstream
    [Netlab platform reference](https://netlab.tools/platforms/).

<a id="containerlab"></a>
[Containerlab](https://containerlab.dev/)
:   The container-based network emulation runtime that Netlab uses as
    its default provider (`provider: clab`). It pulls vendor NOS
    container images (FRR, SR Linux, Arista cEOS, …) and wires them
    together. See
    [Netlab host setup](../40-deployment/10-netlab-host-setup.md) and
    the upstream
    [Containerlab kinds reference](https://containerlab.dev/manual/kinds/).

<a id="frr"></a>
[FRR (FRRouting)](https://frrouting.org/)
:   The open-source software router used as the default device kind in
    most Remote Lab topologies. CI-friendly, no license, boots in
    seconds. The right call for protocol tests (BGP, OSPF, IS-IS) when
    you do not need vendor CLI semantics. See
    [Vendors & images → FRRouting](../40-deployment/30-vendor-images.md#frrouting-device-frr).

<a id="srlinux"></a>
[Nokia SR Linux](https://www.nokia.com/networks/data-center/service-router-linux-NOS/)
:   Nokia's container-native NOS — a real network operating system
    distributed as a public Docker image, free to use under Nokia's
    EULA. Used when a real vendor environment is needed without a
    commercial license. See
    [Vendors & images → Nokia SR Linux](../40-deployment/30-vendor-images.md#nokia-sr-linux-device-srlinux)
    and the upstream
    [SR Linux learning portal](https://learn.srlinux.dev/).

<a id="cisco-iol"></a>
[Cisco IOL](https://netlab.tools/platforms/cisco_iol/)
:   IOS-on-Linux, the IOS image packaged for Containerlab via the
    [hellt/vrnetlab fork](https://github.com/hellt/vrnetlab/). License
    required (Cisco Modeling Labs subscription or partner programme).
    Use only when the test depends on IOS CLI semantics. See
    [Vendors & images → Cisco IOL](../40-deployment/30-vendor-images.md#cisco-iol-device-cisco_iol-license-required).

<a id="subnet-router"></a>
Subnet router
:   A [Tailscale](https://tailscale.com/kb/) node configured to advertise
    a lab subnet's routes to the rest of the mesh, so remote clients can
    reach container management IPs without direct Layer 2 adjacency. The
    Remote Lab host itself typically runs as the subnet router. See
    [Headscale VPN → Remote Lab host (subnet router)](../40-deployment/20-headscale-vpn.md#71-remote-lab-host-subnet-router).

<a id="headscale"></a>
[Headscale](https://headscale.net/)
:   An open-source, self-hosted implementation of the Tailscale control
    plane. The recommended enclosure for a Remote Lab host — the
    HTTP service has no authentication, so a private mesh between the
    lab host and its clients is non-negotiable. See
    [Headscale VPN](../40-deployment/20-headscale-vpn.md) and the
    upstream [Headscale repo](https://github.com/juanfont/headscale).

<a id="headplane"></a>
[Headplane](https://github.com/tale/headplane)
:   A web UI for managing Headscale (users, nodes, advertised routes).
    Deployed alongside Headscale via Docker Compose in the recipe
    shipped here. See
    [Headscale VPN](../40-deployment/20-headscale-vpn.md).

<a id="tailscale"></a>
[Tailscale](https://tailscale.com/kb/)
:   The mesh VPN whose protocol Headscale implements. Each Remote Lab
    client runs the Tailscale agent and joins the tailnet to reach the
    lab host's management address and the advertised lab subnet. See
    [Headscale VPN](../40-deployment/20-headscale-vpn.md).

---

## Peer-project terminology bridge

These terms are owned by other repos in the neops ecosystem. An External
API user arriving from a peer project may meet them in conversation or in
neighbouring docs; this section records Remote Lab's stance on each so
the mental model transfers cleanly.

| Term | Owned by | Remote Lab's stance |
|---|---|---|
| <a id="function-block"></a>Function block | [neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py) | **Not applicable.** Remote Lab provides the topology that function-block tests exercise; it has no notion of function blocks itself. |
| <a id="worker"></a>Worker | [neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py) | **Not applicable.** Remote Lab's analogous roles are *client* (any HTTP caller, including the pytest fixture) and *server* (the FastAPI service). |
| <a id="workflow"></a>Workflow | [neops-workflow-engine](https://github.com/zebbra/neops-workflow-engine) | **Not applicable.** Topology YAML uploaded to Remote Lab is *Netlab* YAML — it describes a network's shape, not a sequence of automation steps. |
| <a id="workflow-engine"></a>Workflow engine | [neops-workflow-engine](https://github.com/zebbra/neops-workflow-engine) | **Not applicable.** Remote Lab runs independently; tests that use both treat them as separate services. |
| <a id="blackboard"></a>Blackboard | [neops-workflow-engine](https://github.com/zebbra/neops-workflow-engine) | **Not applicable.** The Remote Lab [session queue](#session-queue) is a different mechanism (FIFO, single-active) serving a different purpose (exclusive lab access). Do not confuse the two. |
| <a id="provider-peer"></a>Provider | [neops-core](https://github.com/zebbra) (1.0) and [Netlab](https://netlab.tools/) | **Consumer of Netlab's meaning; not applicable to neops-core's.** Remote Lab's `provider:` field in a topology is always Netlab's sense (`clab`, `libvirt`, …) — never the neops-core legacy automation-class sense. |
| <a id="checks"></a>Checks | [neops-core](https://github.com/zebbra) | **Not applicable.** Remote Lab does not produce, store, or interpret `checks`; tests that generate them do so through the worker SDK or neops-core APIs, independently of the lab service. |
| <a id="scope"></a>Scope | [neops-core](https://github.com/zebbra) | **Not applicable.** Remote Lab has no tenancy model — every caller reaches the same lab host; access control is the VPN/firewall boundary. |
| <a id="context"></a>Context | [neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py) | **Not applicable.** Remote Lab exposes device information via [`DeviceInfoDto`](#deviceinfodto); the shape is deliberately flat and unrelated to the worker SDK's `WorkflowContext`. |
| <a id="heartbeat-peer"></a>Heartbeat (peer-project contrast) | [neops-workflow-engine](https://github.com/zebbra/neops-workflow-engine) (and others) | **Defines its own.** Remote Lab's [`POST /session/heartbeat`](#heartbeat) keeps a client's session alive against the lab server, not against any other peer service. Same word, different scope. |

---

## Where to go next

- **[REST API](../30-server/10-rest-api.md)** — endpoint-by-endpoint
  reference; the *Sessions and queueing* and *Labs and topologies*
  sections above both deep-link into it.
- **[Invariants & internals](../50-contributing/20-invariants.md)** —
  the load-bearing rules behind the *Locking and concurrency* and
  *Data models* sections.
- **[Lab lifecycle](../10-concepts/30-lab-lifecycle.md)** — the state
  machine behind every *Labs and topologies* term.
- **[Pytest fixtures](../20-client/10-pytest-fixtures.md)** — the
  Python surface behind every *Testing & client* term.
