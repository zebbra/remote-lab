---
page_purpose: how-to
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# Test Environment Setup

## Install the Package

Add `neops-remote-lab` as a dev dependency in the project that contains your tests:

```bash
# pip
pip install neops-remote-lab

# uv
uv add --group dev neops-remote-lab
```

The package registers a pytest plugin via the `pytest11` entry point. Once installed, the `remote_lab_client` session fixture and the test ordering plugin activate automatically -- no `conftest.py` imports or `pytest_plugins` declarations needed. To confirm:

```bash
pytest --co -q
# You should see your test items collected without import errors
```

To disable the plugin for a specific run (e.g., running unit tests that do not need lab fixtures):

```bash
pytest -p no:neops-remote-lab
```

## Environment Variables

Set these in your shell, a `.env` file, or your CI pipeline:

| Variable | Required | Purpose | Default |
|----------|----------|---------|---------|
| `REMOTE_LAB_URL` | **Yes** for `remote_lab_fixture` | Base URL of the Remote Lab server (e.g., `http://192.168.1.10:8000`). The session-scoped `remote_lab_client` fixture raises `RuntimeError` at startup if this is unset. | *(unset)* |
| `REMOTE_LAB_REQUEST_TIMEOUT` | No | Per-HTTP-request timeout (seconds) | `30` |
| `REMOTE_LAB_SESSION_TIMEOUT` | No | Max seconds to wait in the session queue | `600` |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | No | Max seconds to wait for lab spin-up | `600` |

`remote_lab_fixture` always uses `RemoteLabClient` to talk to the server — there is no automatic fallback to local execution. To run Netlab directly on your workstation without a server in between, call `LabManager` yourself in a project-local fixture; see [Local Lab Testing](20-local-testing.md). For the full variable reference including server-side settings, see [Configuration](../20-server/20-configuration.md).

## conftest.py Patterns

Declare your topology fixtures at module level in `conftest.py`. Each call to `remote_lab_fixture()` creates a function-scoped pytest fixture that acquires a lab, yields the device list, then releases it:

```python
# tests/conftest.py
from neops_remote_lab.testing.fixture import remote_lab_fixture

# One fixture per topology file
simple_frr = remote_lab_fixture("tests/topologies/simple_frr.yml")

# Reuse the same lab across multiple tests (reference-counted)
ospf_lab = remote_lab_fixture(
    "tests/topologies/ospf.yml",
    reuse_lab=True,
)

# Custom fixture name (when two topologies share the same file stem)
dc_spine = remote_lab_fixture(
    "tests/topologies/dc/spine.yml",
    name="dc_spine",
)
```

Tests request the fixture by its name:

```python
# tests/test_routing.py
def test_frr_neighbors(simple_frr):
    for device in simple_frr:
        assert device.name  # DeviceInfoDto with .name and .raw
```

Key points:

- Topology paths are resolved at import time. A missing file raises `FileNotFoundError` before collection starts.
- Each fixture name must be unique across the test suite.
- A test may depend on at most **one** Remote Lab fixture. Requesting multiple fixtures causes a `ValueError` at collection time.

For the full fixture API and ordering plugin details, see [Pytest Fixtures](../30-client/20-pytest-fixtures.md).

## Directory Structure Conventions

A typical project layout:

```
my-project/
  tests/
    conftest.py              # remote_lab_fixture declarations
    topologies/
      simple_frr.yml         # Netlab topology files
      ospf.yml
    test_routing.py           # tests that use lab fixtures
    test_interfaces.py
  pyproject.toml              # neops-remote-lab in dev dependencies
```

Keep topology files in a dedicated `tests/topologies/` directory. Paths in `remote_lab_fixture()` are relative to the working directory where you run `pytest` (typically the project root).

## Dev Dependencies

Beyond `neops-remote-lab` itself, you need:

- **pytest** -- the fixture factory produces standard pytest fixtures
- **Netlab** -- required only if you run tests in [local mode](20-local-testing.md) (i.e., calling `LabManager` directly from your own fixtures). Remote mode delegates all Netlab operations to the server.

If your project uses `uv`, a minimal dev group looks like:

```toml
[dependency-groups]
dev = [
    "neops-remote-lab",
    "pytest",
]
```

## Next Steps

- [Local Lab Testing](20-local-testing.md) -- run tests with Netlab on your machine
- [Remote Lab Testing](30-remote-testing.md) -- run tests against a shared server
