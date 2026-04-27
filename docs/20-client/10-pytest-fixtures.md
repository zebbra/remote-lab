---
title: Pytest Fixtures
description: The stable public API for lab-backed tests — `remote_lab_fixture` factory, the `remote_lab_client` session fixture, and the one-fixture-per-test rule.
tags: [reference, testing, api]
crosslink_defines: []
crosslink_references: []
---

# Pytest Fixtures

`remote_lab_fixture` is the stable public API of this project. It is imported
directly by the [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/)
to give [function-block](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/)
tests a real Netlab topology to run against
([integration guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/)),
and its signature is part of that contract — changes are considered
breaking and require a major version bump.

If you are writing tests, this is the page you want. If you need to drive the
server from a script, see the [RemoteLabClient reference](20-python-client.md)
instead.

!!! info "How the plugin loads"
    Installing `neops-remote-lab` registers a pytest plugin via the package's
    entry points. You do not add anything to `conftest.py` to enable it; you
    only need to import `remote_lab_fixture` at module scope where you want
    a fixture.

---

## `remote_lab_fixture` (factory)

```python
from neops_remote_lab.testing.fixture import remote_lab_fixture

remote_lab_fixture(
    topology: str | Path,
    *,
    name: str | None = None,
    reuse_lab: bool = False,
) -> pytest.fixture
```

Creates a function-scoped pytest fixture bound to a Netlab topology. Call it
at module level in `conftest.py` or in your test file — the return value is
a real `pytest.fixture`, so assigning it to a name makes that name available
to any test in the same collection scope.

### Arguments

| Argument | Type | Default | Description |
|---|---|---|---|
| `topology` | `str \| Path` | – | Path to a Netlab `.yml` file. Expanded (`~`) and resolved to an absolute path at factory call time. The file must exist at factory call time. |
| `name` | `str \| None` | `None` (keyword-only) | Fixture name override. When omitted, the fixture name defaults to the topology file's stem (e.g. `demo.yml` → `demo`). |
| `reuse_lab` | `bool` | `False` (keyword-only) | When `True`, the acquire call uses `reuse=true`; the server increments the reference count on an already-running lab with the same content hash instead of refusing. |

### Raises

- **`FileNotFoundError`** when the resolved topology path does not exist. This happens at factory call time — during test collection — so typos fail before any test runs. <!-- trace: neops_remote_lab/testing/fixture.py:72 -->

### Returns

A pytest fixture of scope `function`. <!-- trace: neops_remote_lab/testing/fixture.py:127 -->
The fixture yields `list[DeviceInfoDto]` — one entry per device in the
running topology.

### What the generated fixture does

On each test that depends on it, the fixture executes this lifecycle:

1. Resolves the session-scoped `remote_lab_client` (creating it on the first
   test that needs a lab).
2. Calls `client.acquire(topology_path, reuse=reuse_lab)`, which blocks
   through the server's 423 polling loop until the lab is running. <!-- trace: neops_remote_lab/testing/fixture.py:124 -->
3. Yields the device list to your test.
4. On teardown — whether the test passed or raised — calls
   `client.release()`. On a `reuse_lab=False` lab this triggers teardown; on
   `reuse_lab=True` it decrements the reference count.

The fixture does not catch exceptions in your test body. An assertion failure
propagates normally and the teardown path still runs release.

### Fixture naming

The name assigned to the factory's return value in your module is what tests
reference. The factory also registers an internal name (the `name` kwarg or
the topology stem) that the collection-time ordering plugin uses to group
tests by shared lab. <!-- trace: neops_remote_lab/testing/fixture.py:84 -->
Alongside the name, the factory stashes the fixture's rank, reuse flag,
topology path, and remote-mode flag in a module-level metadata dict that
the ordering plugin reads at collection time. <!-- trace: neops_remote_lab/testing/fixture.py:93 -->

```python title="Naming examples" linenums="1"
# Fixture usable as `demo_lab`; registered under "demo" (topology stem).
demo_lab = remote_lab_fixture("tests/topologies/demo.yml")

# Same underlying topology, distinct registered name for ordering.
demo_lab_b = remote_lab_fixture(
    "tests/topologies/demo.yml",
    name="demo-second-run",
)

# Reuse enabled: every test using `shared_lab` reuses the running instance.
shared_lab = remote_lab_fixture(
    "tests/topologies/demo.yml",
    reuse_lab=True,
)
```

!!! tip "Use reuse for fast suites"
    For a suite of many small assertions against the same topology, declare
    one `reuse_lab=True` fixture and point every test at it. The first test
    pays the `netlab up` cost; the rest run in seconds.

---

## `remote_lab_client` (session-scoped fixture)

A single `RemoteLabClient` is shared across every test in a pytest session.
You rarely depend on it directly — `remote_lab_fixture` pulls it in for you
— but you can request it when you need the underlying client API inside a
test.

### Behavior

- **Scope:** `session`. Exactly one client per pytest process.
- **Created lazily** on the first test that requests it (directly or via a
  `remote_lab_fixture`).
- **Fails fast** if `REMOTE_LAB_URL` is not set when the fixture is first
  resolved, raising `RuntimeError` with a pointed error message. <!-- trace: neops_remote_lab/testing/fixture.py:34 -->
- **Honors timeout overrides.** When `REMOTE_LAB_REQUEST_TIMEOUT`,
  `REMOTE_LAB_SESSION_TIMEOUT`, or `REMOTE_LAB_ACQUISITION_TIMEOUT` are set
  in the environment, they override the client's defaults. <!-- trace: neops_remote_lab/testing/fixture.py:41 -->
- **Teardown.** Both a pytest session finalizer and an `atexit` handler call
  `client.close()`, so the session is always ended even on abnormal pytest
  exit (SIGINT, worker crash).

### Directly requesting the client

```python title="tests/test_advanced.py" linenums="1"
def test_fetch_devices_directly(remote_lab_client, demo_lab):
    # `demo_lab` already acquired the lab; the session is ACTIVE.
    # `remote_lab_client` lets you poke the server directly.
    assert remote_lab_client.session_id != ""
    assert len(demo_lab) == 2
```

---

## The one-fixture-per-test rule

!!! danger "One `remote_lab_fixture` per test — checked at collection time"
    A test may depend on at most **one** fixture created by
    `remote_lab_fixture`. Requesting two causes pytest collection to fail
    with `ValueError` — the tests never run. <!-- trace: neops_remote_lab/testing/pytest_order_plugin.py:88 -->

### Why

The server enforces one-lab-per-host as a Netlab limitation. A single test
holding two lab fixtures would deadlock at acquire — the second acquire
would sit in the 423 polling loop forever, because the first acquire's
session still holds the host.

The plugin catches this at collection so you see the error immediately, not
after `pytest` has spent five minutes running earlier tests.

### What it looks like when it fails

```python title="A test that will fail collection" linenums="1"
lab_a = remote_lab_fixture("tests/topologies/a.yml")
lab_b = remote_lab_fixture("tests/topologies/b.yml")


def test_cross_topology(lab_a, lab_b):  # (1)
    ...
```

1. Requesting two lab fixtures in a single test. Pytest never executes
   `test_cross_topology` — it errors out of collection first.

!!! failure "Collection error you'll see"
    ```
    ValueError: Test tests/test_cross.py::test_cross_topology uses multiple
    Remote Lab fixtures: lab_a, lab_b. Only one Remote Lab fixture per test
    is allowed.
    ```

### How to work around it

Split the scenario into two tests. If the scenario requires two topologies
to run back-to-back in the same process, use `reuse_lab=True` on one and
sequence them via pytest's normal ordering — which, for lab fixtures, the
plugin deterministically groups by fixture rank (see below).

---

## Test execution ordering

The plugin reorders collected tests so that every test using the same lab
fixture runs in one contiguous block. Within that block, the original
collection order is preserved. <!-- trace: neops_remote_lab/testing/pytest_order_plugin.py:108 -->

Rank is assigned at factory-call time by a monotonically increasing counter
— the first `remote_lab_fixture(...)` call in the module gets rank 0, the
next rank 1, and so on. Reorganizing your `conftest.py` therefore changes
the run order; pin the order intentionally or leave it to topology-stem
alphabetical.

```
Without reordering:  test_a(lab1), test_b(lab2), test_c(lab1)
                     -> two teardowns of lab1 if reuse_lab=False

With the plugin:     test_a(lab1), test_c(lab1), test_b(lab2)
                     -> one teardown of lab1, one acquire of lab2
```

!!! tip "Running `pytest --log-cli-level=info` to see the order"
    The plugin logs the computed execution order to the `remote-lab-plugin`
    logger at INFO level, including topology, reuse flag, and the node IDs
    in each group. Add `--log-cli-level=info` while debugging to watch
    pytest's grouping decisions.

---

## End-to-end example

```python title="tests/conftest.py" linenums="1"
--8<-- "examples/pytest_fixtures/conftest.py"
```

```python title="tests/test_frr_ospf.py" linenums="1"
--8<-- "examples/pytest_fixtures/test_frr_ospf.py"
```

Run the whole file:

```bash
export REMOTE_LAB_URL="http://$LAB_HOST:8000"
pytest tests/test_frr_ospf.py -v
```

!!! success "Expected output (abbreviated)"
    ```
    tests/test_frr_ospf.py::test_two_routers_present PASSED
    tests/test_frr_ospf.py::test_devices_reported_by_netlab PASSED
    tests/test_frr_ospf.py::test_device_names_are_stable PASSED
    3 passed
    ```

Only the first test pays the `netlab up` cost; the remaining tests reuse the
running lab and release at the end of the pytest session.

---

## Ecosystem note

`remote_lab_fixture` is the import path that `neops-worker-sdk-py` uses when
composing its own lab-backed function-block test harness. Downstream test
code written against this API in worker-sdk-py is expected to keep working
across patch and minor versions of this project. If you are maintaining this
project, treat `remote_lab_fixture`'s signature, `remote_lab_client`'s name
and scope, and the one-fixture-per-test rule as a public interface — change
them only when you're ready to coordinate a major-version release with
downstream consumers.

---

## See also

- [RemoteLabClient reference](20-python-client.md) — the HTTP client the
  fixtures wrap.
- [Lab lifecycle](../10-concepts/30-lab-lifecycle.md) — reference counting and reuse semantics
  (relevant when `reuse_lab=True`).
- [Topology format](../10-concepts/40-topology-format.md) — what to put in the `.yml` file.
- [Configuration](../30-server/20-configuration.md) — environment variables that the
  `remote_lab_client` fixture reads.
