---
page_purpose: how-to
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# Local Lab Testing

`remote_lab_fixture` is a **remote-only** fixture — it always talks to a Remote Lab Manager service reachable at `REMOTE_LAB_URL`, and raises `RuntimeError` at session startup if the variable is unset (see `neops_remote_lab/testing/fixture.py:32-34`). If you want to run Netlab topologies directly on your workstation **without** a Remote Lab server in between, call the `LabManager` class directly from your own pytest fixture or test code. This page shows that pattern.

!!! info "Why isn't there a fixture for this?"
    The pytest fixture is intentionally one-track: it always uses HTTP. This keeps the public API stable for shared CI runs and forces a conscious choice when you want to bypass the server. Local-mode tests live in their own `conftest.py` so the boundary stays explicit.

## Prerequisites

- **Netlab installed and working** on the machine where tests run. Verify with:

    ```bash
    netlab version
    netlab test clab
    ```

- **Container runtime** — Containerlab (Docker/Podman) or libvirt, depending on your topology's virtualization provider.
- **No `REMOTE_LAB_URL` requirement** — `LabManager.acquire()` reads the topology file directly from disk; it does not consult any environment variable.

## Direct `LabManager` use (local mode)

Import `LabManager` and call `acquire()` / `release()` yourself. The simplest pattern wraps the calls in a function-scoped pytest fixture inside a project-local `conftest.py`:

```python
# tests/conftest.py
from pathlib import Path
from collections.abc import Iterator

import pytest

from neops_remote_lab.netlab.lab_manager import LabManager
from neops_remote_lab.models import DeviceInfoDto


@pytest.fixture(scope="function")
def local_frr_lab() -> Iterator[list[DeviceInfoDto]]:
    """Function-scoped local lab using LabManager directly (no Remote Lab server)."""
    topology = Path("tests/topologies/simple_frr.yml").resolve()
    devices = LabManager.acquire(topology, reuse=False)
    try:
        yield devices
    finally:
        LabManager.release(topology)
```

A test consumes the fixture exactly like the remote variant:

```python
# tests/test_local.py
def test_two_devices(local_frr_lab):
    assert len(local_frr_lab) == 2
    # device.raw carries the inspected node payload (management IP, container info, etc.)
    for device in local_frr_lab:
        assert device.name
```

The authoritative API is `neops_remote_lab/netlab/lab_manager.py` — see `LabManager.acquire()` for the full signature and the `reuse` semantics.

!!! note "`reuse` defaults differ from the fixture"
    `LabManager.acquire(topo)` defaults `reuse=True`. The pytest factory `remote_lab_fixture(...)` defaults `reuse_lab=False`. Pass `reuse=False` to `acquire()` if you want fresh-state semantics matching the fixture.

## Cross-process safety with `GLOBAL_LOCK`

`LabManager` enforces the one-lab-per-host rule across processes with a system-wide file lock. When two pytest workers (or two terminal sessions) both call `LabManager.acquire()`, only one proceeds; the other blocks in a 2-second retry loop until the lock is released.

```python
# Defined in neops_remote_lab/netlab/lab_manager.py
GLOBAL_LOCK = FileLock(str(Path(tempfile.gettempdir()) / "netlab_pytest.lock"))
```

All lifecycle operations on `LabManager` (acquire, release, teardown) hold this lock. The lock file lives in the system temp directory (e.g., `/tmp/netlab_pytest.lock`).

**Stale lock recovery:** `filelock` uses OS-level advisory locks, so the lock is automatically released when the holding process exits — even on crash. You should not normally need to delete the lock file manually. However, if you see `filelock` errors after a hard kill (`kill -9`), remove the lock file:

```bash
rm /tmp/netlab_pytest.lock
```

## Running tests

```bash
# Run the full suite
pytest -q

# Run with log output to see lab lifecycle events
pytest -s --log-cli-level=INFO
```

The first test to acquire a lab triggers `netlab up`, which can take several minutes for complex topologies. Subsequent tests reusing the same topology (with `reuse=True`) skip this step entirely.

## Topology reuse

When `reuse=True`, `LabManager` matches topologies by **content hash** (SHA-256), not filename. Two files with identical content are treated as the same topology, even if their names differ. Any change to the file — including whitespace — produces a different hash and forces a fresh lab.

This means you can safely rename topology files without triggering unnecessary rebuilds, but editing a topology mid-session will cause the next test group to tear down and rebuild. See [Topology Format](../10-concepts/40-topology-format.md) for the full topology contract and [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md) for state-transition details.

## When to use local mode vs. remote mode

| Aspect | Local mode (`LabManager` direct) | Remote mode (`remote_lab_fixture`) |
|--------|---------------------------------|-----------------------------------|
| Netlab required on test machine | Yes | No |
| Lab sharing across machines | Not possible | Built-in via session queue |
| CI without Netlab installed | Not possible | Works — only the server needs Netlab |
| Concurrent test suites | Serialized via `GLOBAL_LOCK` | Queued via server sessions |
| Heartbeat / stale detection | Not applicable | Automatic |
| Topology upload | N/A (local filesystem) | Multipart upload to server |
| Public API stability | `LabManager` is internal — no semver guarantee | `remote_lab_fixture` is the stable public API |

Local mode is best for laptop development and one-machine experiments. For CI pipelines and shared infrastructure, use [Remote Lab Testing](30-remote-testing.md) — the `remote_lab_fixture` cannot be used in local mode and will not transparently fall back.

## Cleanup

`LabManager` registers an `atexit` handler that tears down the running lab when the Python process exits. This covers normal exits and most crash scenarios. For cases where cleanup did not happen (e.g., `kill -9`), you may have a stale Netlab instance:

```bash
# Check for running netlab instances
netlab status

# Tear down manually
netlab down --cleanup
```

See [Lab Lifecycle — Cleanup](../10-concepts/30-lab-lifecycle.md#cleanup) for all cleanup paths.
