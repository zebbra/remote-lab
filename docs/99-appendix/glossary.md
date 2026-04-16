---
page_purpose: reference
personas_served: [junior-network-engineer, devops-engineer]
difficulty_level: beginner
---

# Glossary

Terms are grouped by domain. Where a concept is explained in depth elsewhere in the docs, a cross-reference link is provided.

## Sessions and Queuing

Session
:   A logical reservation in the Remote Lab server's FIFO queue. A session is created via `POST /session` and identified by a UUID. It progresses from `WAITING` to `ACTIVE` and is removed when the client ends it or it times out. See [Session Queue](../10-concepts/20-session-queue.md).

Session Queue
:   The server-side FIFO list that serializes access to the lab host. Only the session at the head of the queue is `ACTIVE`; all others are `WAITING`. When the active session ends, the next one is promoted. See [Session Queue](../10-concepts/20-session-queue.md).

Active Session
:   A session at position 0 in the queue. Only an active session may call lab endpoints (`POST /lab`, `GET /lab`, `POST /lab/release`, etc.). Non-active sessions receive `423 Locked`.

Waiting Session
:   A session behind at least one other session in the queue. The client polls `GET /session/{id}` to watch its position. Waiting sessions are dropped automatically after a configurable inactivity timeout.

Heartbeat
:   A `POST /session/heartbeat` call that resets the session's staleness timer. The server uses `last_seen_at` timestamps to detect idle sessions; an active session without a heartbeat within the staleness window is cleaned up and the next session is promoted. See [REST API](../20-server/10-rest-api.md).

X-Session-ID
:   The HTTP header used to propagate session identity. Returned in the `POST /session` response, it must be included on all `/lab/*` endpoints and on `/session/heartbeat`. It is the only access boundary -- there is no separate authentication. See [REST API](../20-server/10-rest-api.md).

## Labs and Topologies

Lab
:   A running Netlab topology on the remote host. A lab is created by uploading a topology file to `POST /lab` and destroyed via `DELETE /lab` or by releasing all references. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

Topology
:   A Netlab YAML file (`.yml`) that declares the network devices, links, and modules to deploy. Uploaded to the server as `multipart/form-data`. See [Your First Lab Session](../getting-started/20-first-lab.md) for a minimal example.

Topology Identity (Content Hash)
:   The SHA-256 digest of a topology file's contents. Two files with different filenames but identical content are the same topology. This hash drives the reuse decision in `LabManager.try_acquire()`. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

Reference Count
:   An integer tracking how many consumers are currently using the running lab. Incremented on each `try_acquire` with `reuse=True`; decremented on `release`. When the count drops to zero the lab becomes idle but remains running until a different topology is requested or cleanup runs.

Lab Reuse
:   Opt-in behavior (`reuse=True` / `reuse_lab=True`) that lets multiple tests or API callers share a single running lab instead of tearing it down between uses. Enabled when the topology content hash matches the currently running lab. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

One-Lab Rule
:   The Netlab constraint that only one topology may run per host at any time. Enforced process-wide by `LabManager` (singleton pattern) and cross-process by `GLOBAL_LOCK`. The session queue is a direct consequence of this rule.

## Locking and Concurrency

GLOBAL_LOCK
:   A `filelock.FileLock` at `<tempdir>/netlab_pytest.lock` that serializes lab operations across multiple OS processes. Any code path that starts, reuses, or tears down a lab must hold this lock. See [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

Single-Instance Lock
:   A separate `FileLock` in `__main__.py` that prevents two Remote Lab server processes from running on the same host. On conflict it logs the PID, user, and hostname of the existing process.

## Data Models

DeviceInfoDto
:   Pydantic model representing a network device inside a running lab. Contains the device `name` and a `raw` dict with the full node inspection output from Netlab. Returned by `POST /lab` and `GET /lab/devices`. See [Data Models](../60-development/20-data-models.md).

## Testing

remote_lab_fixture
:   A factory function that creates a function-scoped pytest fixture for a given topology file. The fixture acquires the lab before the test and releases it afterward. Accepts `topology`, `name`, and `reuse_lab` parameters. See [Pytest Fixtures](../30-client/20-pytest-fixtures.md).

remote_lab_client
:   A session-scoped pytest fixture that creates and manages a single `RemoteLabClient` instance for the entire test session. Fails fast if `REMOTE_LAB_URL` is not set. See [Pytest Fixtures](../30-client/20-pytest-fixtures.md).

Fixture Rank
:   An auto-incremented integer assigned to each `remote_lab_fixture` in declaration order. The ordering plugin uses ranks to group tests by topology, minimizing unnecessary lab teardown/rebuild cycles.

## Networking and Infrastructure

Netlab
:   The network lab orchestration tool (`netlab` CLI) that Remote Lab wraps. Netlab coordinates Containerlab (or libvirt) and Ansible to deploy, configure, and tear down virtual network topologies. See [netlab.tools](https://netlab.tools). See also [Netlab Installation](../50-deployment/10-netlab-configuration.md).

Containerlab
:   A container-based network emulation tool that Netlab uses as its default provider (`provider: clab`). It spins up network OS containers (FRR, Nokia SR Linux, Arista cEOS, etc.) and wires them together. See [containerlab.dev](https://containerlab.dev).

Headscale
:   An open-source, self-hosted implementation of the Tailscale control plane. Used in Remote Lab deployments to coordinate VPN mesh connectivity between the lab host and clients. See [Headscale VPN](../50-deployment/20-headscale-vpn.md).

Headplane
:   A web UI for managing Headscale. Provides user, node, and route management through a browser. Deployed alongside Headscale via Docker Compose. See [Headscale VPN](../50-deployment/20-headscale-vpn.md).

Subnet Router
:   A Tailscale node configured to advertise lab subnet routes to the rest of the mesh, allowing remote clients to reach container management IPs without direct Layer 2 adjacency. The Remote Lab VM typically runs as a subnet router.

