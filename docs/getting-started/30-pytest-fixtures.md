---
page_purpose: tutorial
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: beginner
---

# Using Pytest Fixtures

The cURL walkthrough from the previous page involved six manual HTTP calls. The `remote_lab_fixture` factory collapses all of that into a single pytest fixture that acquires the lab before your test and releases it after.

## Declare a fixture

In your project's `conftest.py`, import the factory and declare a fixture for your topology file:

```python title="tests/conftest.py"
from neops_remote_lab.testing.fixture import remote_lab_fixture

# Declare a fixture named after the topology file stem ("simple_frr").
# reuse_lab=True lets multiple tests share the same running topology
# instead of tearing down and rebuilding between each test.
frr_lab = remote_lab_fixture(
    "tests/topologies/simple_frr.yml",
    reuse_lab=True,
)
```

That single call creates a function-scoped pytest fixture called `frr_lab`. Under the hood it:

1. Depends on a session-scoped `remote_lab_client` fixture that creates the HTTP session and waits in the queue
2. Calls `remote_lab_client.acquire()` with your topology (the same `POST /lab` you did manually)
3. Yields a list of `DeviceInfoDto` objects -- one per node in the topology
4. Calls `remote_lab_client.release()` when the test finishes

!!! info "No plugin registration needed"
    The package registers itself as a pytest plugin via the `pytest11` entry point. As long as `neops-remote-lab` is installed in your environment, the `remote_lab_client` fixture and the test-ordering plugin are available automatically.

## Write a test

Use the fixture name (`frr_lab`) as a test parameter. pytest injects the device list:

```python title="tests/test_topology.py"
def test_frr_devices_are_available(frr_lab):
    """Verify the topology came up with the expected nodes."""
    device_names = [d.name for d in frr_lab]
    assert "r1" in device_names
    assert "r2" in device_names


def test_device_has_raw_data(frr_lab):
    """Each device carries the full netlab inspect output."""
    for device in frr_lab:
        assert device.name  # non-empty name
        assert isinstance(device.raw, dict)  # raw netlab inspect data
```

Each `DeviceInfoDto` has two fields:

- **`name`** -- the node name from the topology (e.g. `r1`, `r2`)
- **`raw`** -- the full `netlab inspect` dictionary for that node, containing management IPs, interfaces, and connection details

## Run the tests

Make sure `REMOTE_LAB_URL` is set, then run pytest:

```bash
export REMOTE_LAB_URL=http://<host>:8000
pytest tests/test_topology.py -v
```

Expected output:

```
tests/test_topology.py::test_frr_devices_are_available PASSED
tests/test_topology.py::test_device_has_raw_data PASSED
```

On the first test, you will see a pause while the lab acquires the topology (the same wait you experienced with cURL). Subsequent tests that share the same fixture with `reuse_lab=True` skip the acquisition entirely.

## What `reuse_lab` does

The `reuse_lab` parameter controls whether the server tears down and rebuilds the topology between tests:

- **`reuse_lab=True`** -- the server keeps the topology running and increments a reference count. When your test finishes, `release()` decrements the count. The lab is only torn down when the count reaches zero. Use this when your tests do not mutate device state, or when startup cost is high.

- **`reuse_lab=False`** (default) -- each test gets a clean topology. The server tears down and rebuilds between tests. Use this when tests modify device configuration and need a fresh starting point.

## Multiple topologies

You can declare multiple fixtures for different topologies. Tests are automatically ordered so that all tests sharing the same fixture run consecutively, minimizing the number of topology rebuilds:

```python title="tests/conftest.py"
from neops_remote_lab.testing.fixture import remote_lab_fixture

frr_lab = remote_lab_fixture(
    "tests/topologies/simple_frr.yml",
    reuse_lab=True,
)

srlinux_lab = remote_lab_fixture(
    "tests/topologies/srlinux.yml",
    reuse_lab=True,
)
```

The ordering plugin groups tests by fixture automatically -- you do not need to manage execution order yourself. All `frr_lab` tests run first, then all `srlinux_lab` tests (in the order they were declared).

## Custom fixture names

By default the fixture is named after the topology file stem. You can override this:

```python
my_lab = remote_lab_fixture(
    "tests/topologies/simple_frr.yml",
    name="my_lab",
    reuse_lab=True,
)
```

The `name` parameter sets the pytest fixture name. Use this when the file stem is not descriptive enough or when you need to avoid naming collisions.

## Next steps

You now have a working pytest integration. From here:

- [Client reference](../30-client/10-remote-lab-client.md) -- full `RemoteLabClient` API details and advanced configuration
- [Pytest fixtures reference](../30-client/20-pytest-fixtures.md) -- fixture factory parameters and test ordering internals
- [Architecture](../10-concepts/10-architecture.md) -- understand the full request flow from fixture to Netlab
