---
page_purpose: explanation
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: beginner
---

# Architecture

Remote Lab is split into two components that communicate over HTTP: a **server** that manages Netlab on a remote VM, and a **client** (with pytest fixtures) that runs wherever your tests run.

## Components

```mermaid
graph LR
    subgraph "Your Machine / CI"
        Tests["pytest test suite"]
        Fixture["remote_lab_fixture"]
        Client["RemoteLabClient"]
    end

    subgraph "Remote Lab VM"
        Server["FastAPI Server<br/>(neops-remote-lab)"]
        Queue["Session Queue"]
        LM["LabManager"]
        Netlab["Netlab CLI"]
        Topo["Containerlab<br/>Topology"]
    end

    Tests --> Fixture
    Fixture --> Client
    Client -- "HTTP (REST API)" --> Server
    Server --> Queue
    Server --> LM
    LM --> Netlab
    Netlab --> Topo
```

### Server

The server is a FastAPI application (`neops_remote_lab/server.py`) that runs on a VM where Netlab and Containerlab are installed. It manages:

- A **session queue** that serializes access so only one client uses the lab at a time (see [Session Queue](20-session-queue.md))
- A **`LabManager`** singleton that orchestrates Netlab topology lifecycle -- start, reuse, teardown (see [Lab Lifecycle](30-lab-lifecycle.md))
- **Stale session cleanup** via an adaptive background task
- **Startup cleanup** of any stale Netlab instances left by a previous crash

The server is started with `neops-remote-lab --host 0.0.0.0 --port 8000`. Only one server instance may run per host, enforced by a `filelock` guard in `__main__.py`.

### Client

The client side has two layers:

1. **`RemoteLabClient`** (`neops_remote_lab/client.py`) -- a session-aware HTTP client that handles session creation, queue polling, lab acquisition, heartbeats, and cleanup. It wraps `requests.Session` with retry logic and timeout configuration.

2. **`remote_lab_fixture`** (`neops_remote_lab/testing/fixture.py`) -- a factory function that produces pytest fixtures. Each fixture declares a topology file and whether the lab can be reused. The fixture depends on a session-scoped `remote_lab_client` fixture that manages the HTTP connection.

The client is consumed by **neops-worker-sdk-py**, which imports `remote_lab_fixture` directly to declare lab fixtures for integration tests. The `remote_lab_fixture` call signature is a stable public API.

## Request Flow

When a pytest test that uses a remote lab fixture runs, the request flows through these layers:

```
pytest collects test
  → fixture function calls remote_lab_client.acquire(topology, reuse=True)
    → RemoteLabClient.acquire() sends POST /lab with topology file
      → FastAPI server receives multipart upload
        → server validates X-Session-ID header (must be ACTIVE)
        → server saves topology to temp directory
        → server calls LabManager.try_acquire(topo, reuse=reuse)
          → LabManager computes SHA-256 of topology content
          → LabManager decides: start new lab, reuse existing, or return None (busy)
            → if starting: run_netlab(["up", topo.name], cwd=workdir)
              → Netlab CLI brings up Containerlab topology
            → if reusing: increment ref_count, return existing devices
      → server returns device list to client
    → RemoteLabClient returns list[DeviceInfoDto]
  → fixture yields device list to test
```

After the test completes, the fixture calls `remote_lab_client.release()`, which sends `POST /lab/release` to decrement the reference count. When the test session ends, `remote_lab_client.close()` sends `DELETE /session/{id}` to clean up.

## Trust Model

Remote Lab operates on an **internal trust model** -- there is no authentication. The `REMOTE_LAB_TOKEN` / Bearer auth mechanism is stubbed out in the client but not implemented on the server.

The only access boundary is the `X-Session-ID` header:

- All `/lab/*` endpoints and `/session/heartbeat` require an `X-Session-ID` header
- The header value must belong to a session in the `ACTIVE` state
- Non-active sessions receive `423 Locked`
- Session IDs are UUID v4 values, generated server-side

This means the server should only be exposed on trusted networks -- behind a VPN or on an internal subnet. It is not designed for public-facing deployment.

## One-Lab-Per-Host Constraint

Netlab supports only a single running topology per host. Remote Lab enforces this at two levels:

1. **Process-wide**: `LabManager` is a singleton with class-level state -- `_current_topo`, `_current_topo_hash`, and `_handle` are class attributes, not instance attributes. There is exactly one active lab handle at any time.

2. **Cross-process**: A `FileLock` (`GLOBAL_LOCK`) using a lockfile in the system temp directory serializes access across multiple pytest worker processes. The lock is acquired during `try_acquire()`, `release()`, `_terminate_current()`, and `cleanup()`.

This constraint also means only one server instance may run per host, enforced separately by a `filelock` guard in `__main__.py` that logs the conflicting PID, user, and host on collision.

??? info "Why not multiple labs?"
    Netlab itself uses a single "default" instance internally. Running `netlab up` while another topology is active produces an error: *"It looks like the lab instance 'default' is already running."* The Remote Lab server works within this limitation rather than trying to circumvent it, which keeps the architecture simple and the failure modes predictable.
