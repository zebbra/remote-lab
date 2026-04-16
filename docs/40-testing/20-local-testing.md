---
page_purpose: how-to
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# Local Lab Testing

Local mode runs Netlab directly on your machine -- no Remote Lab server required. This is the default behavior when `REMOTE_LAB_URL` is **not set**. The `LabManager` handles topology lifecycle, enforces the one-lab-per-host rule, and serializes access across processes.

## Prerequisites

- **Netlab installed and working** on the machine where tests run. Verify with:

    ```bash
    netlab version
    netlab test clab
    ```

- **Container runtime** -- Containerlab (Docker/Podman) or libvirt, depending on your topology's virtualization provider.
- **No `REMOTE_LAB_URL`** in the environment. Unset it if needed:

    ```bash
    unset REMOTE_LAB_URL
    ```

## How Local Acquisition Works

When a test requests a `remote_lab_fixture`, the fixture factory detects that `REMOTE_LAB_URL` is not set and calls `LabManager.acquire()` instead of going through the HTTP client. The acquisition flow:

1. `acquire()` calls `try_acquire()` in a loop, sleeping 2 seconds between retries if the lab is busy
2. `try_acquire()` grabs the `GLOBAL_LOCK` (a file-based lock), then:
    - If no lab is running, copies the topology to a temp directory and runs `netlab up`
    - If the same topology is already running and `reuse_lab=True`, increments the reference count and returns the existing device list
    - If a different topology is needed, waits for the current lab's reference count to drop to zero, tears it down, then starts the new one
3. On test teardown, `release()` decrements the reference count. When it reaches zero, the lab becomes idle (still running) until a different topology is requested or the process exits

For a deeper look at state transitions and reference counting, see [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

## Cross-Process Safety with GLOBAL_LOCK

Netlab supports only one active topology per host. If you run multiple pytest processes (e.g., `pytest-xdist` workers or separate terminal sessions), they would collide without coordination. `LabManager` prevents this with a `FileLock`:

```python
GLOBAL_LOCK = FileLock(str(Path(tempfile.gettempdir()) / "netlab_pytest.lock"))
```

All critical operations -- acquisition, release, teardown -- hold this lock. The effect:

- Only one process can start or stop a lab at any time
- A second process calling `acquire()` blocks in its retry loop until the lock is released
- The lock file lives in the system temp directory (e.g., `/tmp/netlab_pytest.lock`)

**Stale lock recovery:** If a process crashes while holding the lock, the file remains on disk. `filelock` uses OS-level advisory locks, so the lock is automatically released when the process exits -- even on a crash. You should not normally need to delete the lock file manually. However, if you see `filelock` errors after a hard kill (e.g., `kill -9`), remove the lock file:

```bash
rm /tmp/netlab_pytest.lock
```

## Running Tests

```bash
# Run the full suite
pytest -q

# Run with log output to see lab lifecycle events
pytest -s --log-cli-level=INFO
```

The first test to request a lab fixture triggers `netlab up`, which can take several minutes for complex topologies. Subsequent tests reusing the same topology skip this step entirely.

## Topology Reuse

When `reuse_lab=True`, `LabManager` matches topologies by **content hash** (SHA-256), not filename. Two files with identical content are treated as the same topology, even if their names differ. Any change to the file -- including whitespace -- produces a different hash and forces a fresh lab.

This means you can safely rename topology files without triggering unnecessary rebuilds, but editing a topology mid-session will cause the next test group to tear down and rebuild.

## Limitations vs. Remote Mode

| Aspect | Local mode | Remote mode |
|--------|-----------|-------------|
| Netlab required on test machine | Yes | No |
| Lab sharing across machines | Not possible | Built-in via session queue |
| CI without Netlab installed | Not possible | Works -- only the server needs Netlab |
| Concurrent test suites | Serialized via `GLOBAL_LOCK` | Queued via server sessions |
| Heartbeat / stale detection | Not applicable | Automatic |
| Topology upload | N/A (local filesystem) | Multipart upload to server |

Local mode is best for development and single-machine testing. For CI pipelines and shared infrastructure, use [Remote Lab Testing](30-remote-testing.md).

## Cleanup

`LabManager` registers an `atexit` handler that tears down the running lab when the Python process exits. This covers normal exits and most crash scenarios. For cases where cleanup did not happen (e.g., `kill -9`), you may have a stale Netlab instance:

```bash
# Check for running netlab instances
netlab status

# Tear down manually
netlab down --cleanup
```

See [Lab Lifecycle -- Cleanup](../10-concepts/30-lab-lifecycle.md#cleanup) for all cleanup paths.
