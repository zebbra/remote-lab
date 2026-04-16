---
page_purpose: tutorial
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: beginner
---

# Using Pytest Fixtures

The cURL walkthrough from the previous page involved six manual HTTP calls. The `remote_lab_fixture` factory collapses all of that into a single pytest fixture that acquires the lab before your test and releases it after.

!!! info "New to pytest?"
    A few terms used below:

    - **[Fixture](../99-appendix/glossary.md#fixture)** -- a setup/teardown hook that pytest injects into your test by name. The function returns (or `yield`s) the value your test receives as a parameter.
    - **[`conftest.py`](../99-appendix/glossary.md#conftestpy)** -- a magic file that pytest auto-discovers in test directories. Anything declared here is available to every test in that directory tree without an `import`.
    - **[Fixture scope](../99-appendix/glossary.md#fixture-scope)** -- how long the fixture's value lives. Function-scoped fixtures (the default) are torn down after each test; session-scoped fixtures are reused for the whole pytest run.

    For a deeper introduction, see the [pytest fixtures explanation](https://docs.pytest.org/en/stable/explanation/fixtures.html).

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

### Concrete example: extract a management IP and SSH in

`raw` mirrors Netlab's `netlab inspect <node>` output. The exact key path depends on the provider and modules, but for the `clab` provider the management IP is reachable at the top-level `ansible_host` field. A quick smoke test:

```python title="tests/test_ssh.py"
import subprocess

def test_r1_is_reachable_via_ssh(frr_lab):
    r1 = next(d for d in frr_lab if d.name == "r1")
    r1_mgmt = r1.raw["ansible_host"]
    assert r1_mgmt, "Netlab did not assign a management IP to r1"

    # A real test would use netmiko/scrapli; here we just prove SSH responds.
    result = subprocess.run(
        ["ssh", "-o", "BatchMode=yes", "-o", "StrictHostKeyChecking=no",
         f"admin@{r1_mgmt}", "show version"],
        capture_output=True, text=True, timeout=10,
    )
    assert result.returncode == 0, result.stderr
```

The `raw` dict carries everything `netlab inspect` knows -- module configuration, interface assignments, peers -- so most network-tooling libraries (netmiko, scrapli, NAPALM) can be wired up by reading the relevant key. See [Data Models -- DeviceInfoDto](../60-development/20-data-models.md#deviceinfodto) for the on-the-wire contract.

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

!!! note "Default differs by layer"
    `reuse_lab` defaults to `False` for the fixture, but the underlying HTTP endpoint and `LabManager` API use different defaults. See [Reuse defaults across layers](../10-concepts/30-lab-lifecycle.md#reuse-defaults-across-layers).

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
