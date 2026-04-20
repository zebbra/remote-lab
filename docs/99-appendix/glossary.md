---
page_purpose: reference
personas_served: [junior-network-engineer, devops-engineer]
difficulty_level: beginner
---

# Glossary

Terms are grouped by domain. Where a concept is explained in depth elsewhere in the docs, a cross-reference link is provided.

## Sessions and Queuing

<a id="session"></a>
Session
:   A logical reservation in the Remote Lab server's FIFO queue. A session is created via `POST /session` and identified by a UUID. It progresses from `WAITING` to `ACTIVE` and is removed when the client ends it or it times out. See [Session Queue](../10-concepts/20-session-queue.md).

Session Queue
:   The server-side FIFO list that serializes access to the lab host. Only the session at the head of the queue is `ACTIVE`; all others are `WAITING`. When the active session ends, the next one is promoted. See [Session Queue](../10-concepts/20-session-queue.md).

Active Session
:   A session at position 0 in the queue. Only an active session may call lab endpoints (`POST /lab`, `GET /lab`, `POST /lab/release`, etc.). Non-active sessions receive `423 Locked`.

Waiting Session
:   A session behind at least one other session in the queue. The client polls `GET /session/{id}` to watch its position. Waiting sessions are dropped automatically after a configurable inactivity timeout.

<a id="heartbeat"></a>
Heartbeat
:   A `POST /session/heartbeat` call that resets the session's staleness timer. The server uses `last_seen_at` timestamps to detect idle sessions; an active session without a heartbeat within the staleness window is cleaned up and the next session is promoted. See [REST API](../20-server/10-rest-api.md). For how this term is used in the wider neops ecosystem, see [Heartbeat (peer-project contrast)](#heartbeat-ecosystem) below.

X-Session-ID
:   The HTTP header used to propagate session identity. Returned in the `POST /session` response, it must be included on all `/lab/*` endpoints and on `/session/heartbeat`. It is the only access boundary -- there is no separate authentication. See [REST API](../20-server/10-rest-api.md).

## Labs and Topologies

Lab
:   A running Netlab topology on the remote host. A lab is created by uploading a topology file to `POST /lab` and destroyed via `DELETE /lab` or by releasing all references. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

<a id="topology"></a>
Topology
:   A Netlab YAML file (`.yml`) that declares the network devices, links, and modules to deploy. Uploaded to the server as `multipart/form-data`. See [Your First Lab Session](../getting-started/20-first-lab.md) for a minimal example.

Topology Identity (Content Hash)
:   The SHA-256 digest of a topology file's contents. Two files with different filenames but identical content are the same topology. This hash drives the reuse decision in `LabManager.try_acquire()`. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

Reference Count
:   An integer tracking how many consumers are currently using the running lab. Incremented on each `try_acquire` with `reuse=True`; decremented on `release`. When the count drops to zero the lab becomes idle but remains running until a different topology is requested or cleanup runs.

Lab Reuse
:   Opt-in behavior (`reuse=True` / `reuse_lab=True`) that lets multiple tests or API callers share a single running lab instead of tearing it down between uses. Enabled when the topology content hash matches the currently running lab. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

One-Lab Rule
:   The Netlab constraint that only one topology may run per host at any time. Enforced process-wide by `LabManager` (a class-only state container -- never instantiated) and cross-process by `GLOBAL_LOCK`. The session queue is a direct consequence of this rule.

## Locking and Concurrency

<a id="labmanager"></a>
LabManager
:   A class-only singleton in `neops_remote_lab/netlab/lab_manager.py` that owns the one running lab per host. It enforces Netlab's one-lab-per-host limitation, holds topology identity (SHA-256), tracks reference counts, and registers an `atexit` teardown. Never instantiated — all methods are classmethods. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

GLOBAL_LOCK
:   A `filelock.FileLock` at `<tempdir>/netlab_pytest.lock` that serializes lab operations across multiple OS processes. Any code path that starts, reuses, or tears down a lab must hold this lock. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

Single-Instance Lock
:   A separate `FileLock` in `__main__.py` that prevents two Remote Lab server processes from running on the same host. On conflict it logs the PID, user, and hostname of the existing process.

## Data Models

DeviceInfoDto
:   Pydantic model representing a network device inside a running lab. Contains the device `name` and a `raw` dict with the full node inspection output from Netlab. Returned by `POST /lab` and `GET /lab/devices`. See [Data Models](../60-development/20-data-models.md).

## Testing

<a id="fixture"></a>
Fixture
:   A pytest setup/teardown hook that produces a value (or `yield`s one) and injects it into a test by parameter name. Remote Lab provides `remote_lab_client` and the `remote_lab_fixture` factory. See the [pytest fixtures explanation](https://docs.pytest.org/en/stable/explanation/fixtures.html).

<a id="fixture-scope"></a>
Fixture Scope
:   How long pytest keeps a fixture's value alive: `function` (per test, default), `class`, `module`, `package`, or `session` (per pytest run). Remote Lab uses `session` for `remote_lab_client` and `function` for fixtures created by `remote_lab_fixture`. See [pytest scope reference](https://docs.pytest.org/en/stable/how-to/fixtures.html#scope-sharing-fixtures-across-classes-modules-packages-or-session).

Fixture Factory
:   A function that returns a pytest fixture. `remote_lab_fixture(topology, ...)` is one -- each call produces a new function-scoped fixture wired to a specific topology file. See [Pytest Fixtures](../30-client/20-pytest-fixtures.md).

<a id="conftestpy"></a>
`conftest.py`
:   A pytest-discovered file in a test directory whose contents (fixtures, hooks, plugins) are auto-loaded for every test in that directory tree without an `import`. Where you typically declare your `remote_lab_fixture(...)` calls. See [pytest conftest reference](https://docs.pytest.org/en/stable/reference/fixtures.html#conftest-py-sharing-fixtures-across-multiple-files).

`pytest11` Entry Point
:   The Python package metadata key (`[project.entry-points.pytest11]` in `pyproject.toml`) that pytest scans on startup to discover plugins. Because `neops-remote-lab` registers itself this way, the `remote_lab_client` fixture and the test-ordering plugin are available as soon as the package is installed -- no `conftest.py` boilerplate needed. See [pytest plugin discovery](https://docs.pytest.org/en/stable/how-to/writing_plugins.html#making-your-plugin-installable-by-others).

remote_lab_fixture
:   A factory function that creates a function-scoped pytest fixture for a given topology file. The fixture acquires the lab before the test and releases it afterward. Accepts `topology`, `name`, and `reuse_lab` parameters. See [Pytest Fixtures](../30-client/20-pytest-fixtures.md).

remote_lab_client
:   A session-scoped pytest fixture that creates and manages a single `RemoteLabClient` instance for the entire test session. Fails fast if `REMOTE_LAB_URL` is not set. See [Pytest Fixtures](../30-client/20-pytest-fixtures.md).

Fixture Rank
:   An auto-incremented integer assigned to each `remote_lab_fixture` in declaration order. The ordering plugin uses ranks to group tests by topology, minimizing unnecessary lab teardown/rebuild cycles.

## Networking and Infrastructure

<a id="netlab"></a>
Netlab
:   The network lab orchestration tool (`netlab` CLI) that Remote Lab wraps. Netlab coordinates Containerlab (or libvirt) and Ansible to deploy, configure, and tear down virtual network topologies. See [netlab.tools](https://netlab.tools). See also [Netlab Installation](../50-deployment/10-netlab-configuration.md).

<a id="containerlab"></a>
Containerlab
:   A container-based network emulation tool that Netlab uses as its default provider (`provider: clab`). It spins up network OS containers (FRR, Nokia SR Linux, Arista cEOS, etc.) and wires them together. See [containerlab.dev](https://containerlab.dev).

<a id="headscale"></a>
Headscale
:   An open-source, self-hosted implementation of the Tailscale control plane. Used in Remote Lab deployments to coordinate VPN mesh connectivity between the lab host and clients. See [Headscale VPN](../50-deployment/20-headscale-vpn.md).

Headplane
:   A web UI for managing Headscale. Provides user, node, and route management through a browser. Deployed alongside Headscale via Docker Compose. See [Headscale VPN](../50-deployment/20-headscale-vpn.md).

Subnet Router
:   A Tailscale node configured to advertise lab subnet routes to the rest of the mesh, allowing remote clients to reach container management IPs without direct Layer 2 adjacency. The Remote Lab VM typically runs as a subnet router.

## Peer-project terminology bridge

Terms below are owned by other projects in the neops ecosystem. This glossary records Remote Lab's stance on each one -- whether the project *defines* the term, *consumes* the term from a peer, or treats the term as *not applicable*. Readers arriving from the worker SDK or workflow engine can use these entries to tell where their mental model transfers cleanly and where it does not.

<a id="function-block"></a>
Function Block
:   Owned by [neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py). A function block is a typed Python class that performs one unit of work (run, acquire, or rollback) against a device or entity inside the neops platform. **Remote Lab's stance: not applicable.** Remote Lab has no notion of function blocks -- it only provides the virtual topology that function block unit tests exercise. See the worker SDK for the canonical definition.

<a id="workflow-engine"></a>
Workflow Engine
:   Owned by [neops-workflow-engine](https://github.com/zebbra/neops-workflow-engine). The NestJS service that validates, schedules, and orchestrates workflow execution across workers. **Remote Lab's stance: not applicable.** Remote Lab runs independently of the workflow engine; tests that happen to use both treat them as separate services.

<a id="blackboard"></a>
Blackboard
:   Owned by [neops-workflow-engine](https://github.com/zebbra/neops-workflow-engine). The engine's job queue where workers poll for pending jobs and push results back. **Remote Lab's stance: not applicable.** The Remote Lab session queue is a different mechanism (FIFO, single-ACTIVE) and serves a different purpose (exclusive access to one lab host); do not confuse the two.

<a id="heartbeat-ecosystem"></a>
Heartbeat (peer-project contrast)
:   In [neops-workflow-engine](https://github.com/zebbra/neops-workflow-engine), a heartbeat is the periodic ping a worker sends to prove liveness to the engine. **Remote Lab's stance: defines its own.** Remote Lab has its own `POST /session/heartbeat` endpoint with the same role but a different scope: it keeps a client's session alive against the lab server, not against the workflow engine. See [Heartbeat](#heartbeat) above for the in-scope definition.

<a id="provider-ecosystem"></a>
Provider
:   In [neops-core](https://github.com/zebbra) (1.0), a `provider` is a Python class implementing network automation logic via Nornir. In Netlab (which Remote Lab wraps), `provider:` is a topology field selecting the virtualization backend (`clab`, `libvirt`, etc.). **Remote Lab's stance: consumer of Netlab's meaning; not applicable to neops-core's meaning.** Remote Lab's `provider:` field in a topology file is always Netlab's sense -- never the neops-core legacy automation-class sense.

<a id="checks-ecosystem"></a>
Checks
:   Owned by [neops-core](https://github.com/zebbra). Versioned key-value records produced by CHECK providers or function blocks that compare device state to expected values. **Remote Lab's stance: not applicable.** Remote Lab does not produce, store, or interpret `checks`; a test that generates checks does so through the worker SDK or neops-core APIs, independent of the lab service.

<a id="scope-ecosystem"></a>
Scope
:   Owned by [neops-core](https://github.com/zebbra). Defines entity visibility and allowed tasks per user role in the CMS. **Remote Lab's stance: not applicable.** Remote Lab has no tenancy model -- every caller reaches the same lab host; access control is the VPN/firewall boundary, not a scope.

<a id="context-ecosystem"></a>
Context
:   In [neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py), the `context` is the typed `WorkflowContext` holding entity data passed between function blocks. **Remote Lab's stance: not applicable.** Remote Lab exposes device information via `DeviceInfoDto` returned from `POST /lab` and `GET /lab/devices`; the shape is different and deliberately flat.

<a id="worker-ecosystem"></a>
Worker
:   Owned by [neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py). A Python process that registers with the engine, polls for jobs, and executes function blocks. **Remote Lab's stance: not applicable.** Remote Lab has no `worker` concept; the analogous roles are "client" (a `RemoteLabClient`, including the pytest fixture) and "server" (the FastAPI service owning the lab host).

<a id="workflow-ecosystem"></a>
Workflow
:   Owned by [neops-workflow-engine](https://github.com/zebbra/neops-workflow-engine). A YAML document declaring an ordered sequence of function block steps. **Remote Lab's stance: not applicable.** Topology YAML files uploaded to Remote Lab are *Netlab* YAML -- they describe a network's shape, not a sequence of automation steps -- and are unrelated to neops workflow definitions.

