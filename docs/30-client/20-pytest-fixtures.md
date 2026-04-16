---
page_purpose: reference
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# Pytest Fixtures

Remote Lab provides a pytest plugin that registers two fixture layers: a session-scoped `remote_lab_client` that manages the HTTP connection, and a `remote_lab_fixture` factory that produces per-topology test fixtures. A companion ordering plugin groups tests by topology to minimize lab teardown/rebuild cycles.

The plugin is auto-registered via the `pytest11` entry point -- installing `neops-remote-lab` is sufficient; no `conftest.py` imports or `pytest_plugins` declarations are needed in consuming projects.

## `remote_lab_fixture()` Factory

Creates a function-scoped pytest fixture that acquires a Netlab topology and yields the device list.

```python
from neops_remote_lab.testing.fixture import remote_lab_fixture

my_lab = remote_lab_fixture(
    topology="topologies/frr_simple.yml",
    name="my_lab",
    reuse_lab=False,
)
```

### Signature

```python
def remote_lab_fixture(
    topology: str | Path,
    *,
    name: str | None = None,
    reuse_lab: bool = False,
) -> Callable[[], Iterator[list[DeviceInfoDto]]]
```

### Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `topology` | `str \| Path` | *(required)* | Path to a Netlab topology `.yml` file. Resolved via `Path.expanduser().resolve()` at fixture creation time. Raises `FileNotFoundError` if the file does not exist. |
| `name` | `str \| None` | `None` | Custom fixture name. Defaults to the topology file's stem (e.g., `frr_simple` for `frr_simple.yml`). Must be unique across all `remote_lab_fixture` calls in the test suite. |
| `reuse_lab` | `bool` | `False` | When `True`, the fixture reuses an existing lab if one is already running with the same topology (matched by content hash). See [Lab Lifecycle -- Reuse vs. Exclusive Access](../10-concepts/30-lab-lifecycle.md#reuse-vs-exclusive-access). |

### Return Value

Returns a **pytest fixture function** with `scope="function"`. When a test requests this fixture, the function:

1. Calls `remote_lab_client.acquire(topology, reuse=reuse_lab)` to obtain the lab
2. Yields `list[DeviceInfoDto]` -- one entry per device, with `name` and `raw` fields (see [RemoteLabClient -- acquire()](10-remote-lab-client.md#acquiretopology-reuse))
3. On teardown (after the test completes), calls `remote_lab_client.release()` to decrement the server's reference count

### Side Effects at Import Time

Calling `remote_lab_fixture()` at module level (which is the intended usage) has immediate side effects:

- The `topology` path is resolved and validated (raises `FileNotFoundError` if missing)
- The fixture is assigned a monotonically increasing **rank** based on creation order
- The fixture name and metadata are registered in `REMOTE_LAB_ORDER` and `REMOTE_LAB_FIXTURE_META` (see [Ordering Registries](#ordering-registries) below)

These registrations happen at import time, before pytest collection. The ordering plugin uses them during the `pytest_collection_modifyitems` hook.

### Usage

Declare fixtures at module level in your `conftest.py` or test modules:

```python
# conftest.py
from neops_remote_lab.testing.fixture import remote_lab_fixture

simple_frr = remote_lab_fixture("topologies/frr_simple.yml")
ospf_lab = remote_lab_fixture("topologies/ospf.yml", reuse_lab=True)
```

Tests request the fixture by name:

```python
def test_frr_routing(simple_frr):
    for device in simple_frr:
        print(f"Device: {device.name}")
        # device.raw contains the full netlab inspect output
```

## `remote_lab_client` Fixture

A session-scoped fixture that creates and manages a single `RemoteLabClient` instance for the entire pytest session.

### Scope and Lifecycle

- **Scope:** `session` -- one client instance shared across all tests
- **Setup:** Creates a `RemoteLabClient`, which immediately creates a server session and waits for it to become `ACTIVE` (see [RemoteLabClient -- Initialization Sequence](10-remote-lab-client.md#initialization-sequence))
- **Teardown:** Calls `client.close()` to end the server session. Also registers `client.close` via `atexit` as a safety net for abnormal interpreter exits.

### Environment Variables

The fixture reads server URL and timeout overrides from the environment:

| Variable | Required | Purpose |
|----------|----------|---------|
| `REMOTE_LAB_URL` | **Yes** | Server base URL. Raises `RuntimeError` if not set. |
| `REMOTE_LAB_REQUEST_TIMEOUT` | No | Overrides `request_timeout` (default 30s) |
| `REMOTE_LAB_SESSION_TIMEOUT` | No | Overrides `session_timeout` (default 600s) |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | No | Overrides `lab_acquisition_timeout` (default 600s) |

Timeout overrides are parsed as integers. Only variables that are set are passed to the `RemoteLabClient` constructor; unset variables leave the constructor defaults in effect.

### Dependency Chain

Every fixture produced by `remote_lab_fixture()` implicitly depends on `remote_lab_client`:

```
test function
  → my_lab fixture (function-scoped, from remote_lab_fixture())
    → remote_lab_client fixture (session-scoped)
      → RemoteLabClient instance
        → server session (HTTP)
```

pytest resolves this dependency automatically. You never need to request `remote_lab_client` directly in a test -- it is injected into the fixture function produced by `remote_lab_fixture()`.

## Test Ordering Plugin

The ordering plugin (`neops_remote_lab.testing.pytest_order_plugin`) reorders collected tests so that tests sharing the same topology fixture run consecutively. This minimizes lab teardown/rebuild cycles -- if three tests use `simple_frr` and two use `ospf_lab`, the `simple_frr` tests run as a group, then the `ospf_lab` tests run as a group.

### How It Works

The plugin implements the `pytest_collection_modifyitems` hook:

1. For each collected test, it checks which `remote_lab_fixture`-based fixtures the test requests
2. Each fixture has a **rank** (assigned at creation time in fixture declaration order)
3. Tests are sorted by `(rank, original_collection_index)` -- grouped by fixture, stable-sorted within each group
4. Tests that do not use any Remote Lab fixture are assigned rank `999` and run last

### Single-Fixture Constraint

A test may depend on at most **one** Remote Lab fixture. If a test requests multiple fixtures created by `remote_lab_fixture()`, the ordering plugin raises `ValueError` during collection:

```
ValueError: Test test_both uses multiple Remote Lab fixtures: simple_frr, ospf_lab.
Only one Remote Lab fixture per test is allowed.
```

This constraint exists because the server supports only one active topology at a time. A test that needs devices from two topologies must be restructured -- either combine the devices into a single topology, or split the test.

### Execution Order Logging

At `INFO` level, the plugin logs a structured summary of the computed execution order, grouped by fixture:

```
================================================================================
REMOTE LAB TEST EXECUTION ORDER
================================================================================

Tests are ordered by their Remote Lab fixture rank (lower rank = earlier execution).
Within each fixture group, tests maintain their original collection order.

Fixture #1: simple_frr
  topology: topologies/frr_simple.yml
  reuse: False
  rank: 0
  tests:
    1. tests/test_frr.py::test_frr_routing
    2. tests/test_frr.py::test_frr_neighbors

Fixture #2: ospf_lab
  topology: topologies/ospf.yml
  reuse: True
  rank: 1
  tests:
    1. tests/test_ospf.py::test_ospf_adjacency
================================================================================
```

Run with `-s --log-cli-level=INFO` to see this output during collection.

## Ordering Registries

Two module-level dictionaries track fixture metadata for the ordering plugin. These are internal but documented here for debugging and advanced use.

### `REMOTE_LAB_ORDER`

```python
REMOTE_LAB_ORDER: dict[str, int]  # fixture_name → rank
```

Maps each fixture name to its rank (creation order). The first `remote_lab_fixture()` call gets rank `0`, the second gets rank `1`, and so on. The ordering plugin uses this to sort tests.

### `REMOTE_LAB_FIXTURE_META`

```python
REMOTE_LAB_FIXTURE_META: dict[str, dict[str, object]]  # fixture_name → metadata
```

Stores metadata for each registered fixture:

| Key | Type | Description |
|-----|------|-------------|
| `rank` | `int` | Same as `REMOTE_LAB_ORDER[name]` |
| `reuse` | `bool` | The `reuse_lab` value passed to `remote_lab_fixture()` |
| `topology` | `str` | Topology path, relative to `cwd` when possible |
| `remote` | `bool` | `True` if `REMOTE_LAB_URL` was set at fixture creation time |

The ordering plugin reads both registries during `pytest_collection_modifyitems`. The execution order log includes `topology`, `reuse`, and `rank` from `REMOTE_LAB_FIXTURE_META`.

## Plugin Auto-Registration

The pytest plugin is registered via the `pytest11` entry point in `pyproject.toml`:

```toml
[project.entry-points.pytest11]
neops-remote-lab = "neops_remote_lab.pytest_plugins"
```

The entry point module (`neops_remote_lab/pytest_plugins.py`) declares the plugin list:

```python
pytest_plugins: list[str] = [
    "neops_remote_lab.testing.fixture",
    "neops_remote_lab.testing.pytest_order_plugin",
]
```

This registers two components:

- **`neops_remote_lab.testing.fixture`** -- provides the `remote_lab_client` session-scoped fixture
- **`neops_remote_lab.testing.pytest_order_plugin`** -- provides the `pytest_collection_modifyitems` hook for test ordering

Because registration uses the `pytest11` entry point, the plugin activates automatically when `neops-remote-lab` is installed in the environment. No `conftest.py` boilerplate is needed. To disable it, use pytest's `-p no:neops-remote-lab` flag.

## Advanced Patterns

### Multiple Topologies

Declare one fixture per topology. Tests are automatically grouped by the ordering plugin:

```python
# conftest.py
from neops_remote_lab.testing.fixture import remote_lab_fixture

frr_lab = remote_lab_fixture("topologies/frr_simple.yml")
ospf_lab = remote_lab_fixture("topologies/ospf.yml")
```

The first topology's tests all run before the second topology's tests begin. Within each group, tests maintain their original collection order.

### Lab Reuse Across Tests

When multiple tests share the same topology and none need exclusive access, enable `reuse_lab` to skip redundant teardown/rebuild cycles:

```python
shared_lab = remote_lab_fixture(
    "topologies/frr_simple.yml",
    reuse_lab=True,
)
```

With `reuse_lab=True`, the server increments a reference count instead of starting a fresh lab. The lab stays running until the last test releases it. This is significantly faster for large topologies.

See [Lab Lifecycle -- Reference Counting](../10-concepts/30-lab-lifecycle.md#reference-counting) for details on how reference counting works.

### Custom Fixture Names

By default, the fixture name is the topology file stem. Override it when you need a more descriptive name or when two topologies share the same stem:

```python
dc_spine = remote_lab_fixture(
    "topologies/dc/spine.yml",
    name="dc_spine",
)
campus_spine = remote_lab_fixture(
    "topologies/campus/spine.yml",
    name="campus_spine",
)
```

The `name` parameter determines both the pytest fixture name (used in test function signatures) and the key in the ordering registries.
