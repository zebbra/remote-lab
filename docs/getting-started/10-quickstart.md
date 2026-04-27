---
title: Quickstart
description: From zero to a passing lab-backed pytest in ten minutes — install, configure, and run your first test against a Remote Lab.
tags: [tutorial, testing, client]
crosslink_defines: []
crosslink_references: []
---

# Quickstart

You have a pytest suite that needs a real router — not a mock, not a container
hand-rolled per test, but a Netlab topology reachable from your local machine
with the same identity every time. This guide takes you from nothing to a
passing lab-backed test against a running Remote Lab Manager.

By the end you will have installed the client package, pointed it at a server,
written a minimal topology, and run a pytest that acquires a lab, lists its
devices, and tears it down cleanly — all with three lines of test code.

!!! info "Before you start"
    You need three things:

    - **Ubuntu 22.04+** (or similar) with **Python 3.11+** and `pipx` available.
    - **`pytest`** installed in your project's virtual environment.
    - **A reachable Remote Lab Manager** — its base URL goes into the
      `REMOTE_LAB_URL` environment variable in step 2.

!!! tip "Don't have a remote server yet?"
    On Ubuntu you can run the server locally and point your tests at
    `http://localhost:8000`. The deep-dive in
    [Local development server](20-local-server.md) walks through the rootless
    Netlab + Containerlab install and a one-command launch. You can finish
    that page and come straight back here.

---

## 1. Install the client package

Install `neops-remote-lab` into the same environment as your tests. The package
ships both the pytest plugin and the HTTP client; no separate install is needed.

```bash title="Install via pip"
pip install neops-remote-lab
```

!!! success "Expected output"
    ```
    Successfully installed neops-remote-lab-<version>
    ```

Verify the package and fixture import cleanly:

```bash
python -c "from neops_remote_lab.testing.fixture import remote_lab_fixture; print('OK')"
```

!!! success "Expected output"
    ```
    OK
    ```

A successful import means the pytest plugin's entry point is registered (the
package's `[project.entry-points.pytest11]` declares `neops-remote-lab` →
`neops_remote_lab.pytest_plugins`) and `remote_lab_fixture` is reachable from
your test code.

---

## 2. Point the client at your Remote Lab

The client reads the Remote Lab Manager URL from the `REMOTE_LAB_URL`
environment variable. The pytest fixture fails fast at session setup if this
variable is missing — no silent fallback to localhost, no default. <!-- trace: neops_remote_lab/testing/fixture.py:34 -->

```bash title="Set the base URL"
# Replace lab.example.com with your Remote Lab Manager hostname (or use
# http://localhost:8000 if you started the server locally — see the tip above).
export REMOTE_LAB_URL="http://lab.example.com:8000"
```

!!! tip "Put it in a .env file"
    For local development, a `.env` loaded by `python-dotenv` or your shell's
    direnv integration keeps this out of your shell history and out of CI
    secrets by accident.

Confirm the server is reachable before you write any test code:

```bash
curl -fsS "$REMOTE_LAB_URL/healthz" && echo OK
```

!!! success "Expected output"
    ```
    OK
    ```

A `204 No Content` on `/healthz` with no body is the liveness signal. Anything
else — a connection error, a `502`, a redirect — means your VPN or Tailscale
tunnel is not up, or the server is not running. Fix that first; the fixture
cannot help you debug transport.

---

## 3. Write a minimal topology

The topology is a Netlab YAML file. `LabManager` enforces the `.yml` extension
internally — `.yaml` will fail when the server attempts to boot — so name the
file `.yml` even though the HTTP surface accepts both.

Create `tests/topologies/demo.yml`:

```yaml title="tests/topologies/demo.yml" linenums="1"
--8<-- "examples/quickstart/demo.yml"
```

1. `clab` selects Containerlab as the underlying launcher. This project is a
   Netlab wrapper; it has no separate Containerlab connector.
2. `frr` (FRRouting) is a fully open-source daemon with no image licensing —
   good default for a first-run topology. Switching to Cisco IOL requires
   licensed images and is out of scope for this quickstart.
3. Shorthand for a point-to-point link between `r1` and `r2`.

!!! warning "Topology files are uploaded verbatim"
    The server identifies topologies by the SHA-256 of their file contents —
    not the filename. Two files with the same bytes but different names are
    treated as one topology; the second upload will reuse the running lab if
    `reuse_lab=True`.

---

## 4. Write the test

Create `tests/conftest.py` to declare the fixture, and `tests/test_demo.py`
to use it. Keep them separate — the factory call belongs at module scope so
pytest can discover the fixture name before collection runs.

```python title="tests/conftest.py" linenums="1"
--8<-- "examples/quickstart/conftest.py"
```

1. The package registers its pytest plugin on install, so `remote_lab_fixture`
   can be imported directly from this module path.
2. The factory returns a real `pytest.fixture(scope="function")` bound to the
   topology. If the file does not exist, this call raises `FileNotFoundError`
   at import time — you find the typo before a single test runs. <!-- trace: neops_remote_lab/testing/fixture.py:72 -->

```python title="tests/test_demo.py" linenums="1"
--8<-- "examples/quickstart/test_demo.py"
```

1. The fixture name `demo_lab` matches the variable in `conftest.py`.
2. The fixture yields a list of `DeviceInfoDto` objects — one per node in the
   topology. Each carries `.name` (from Netlab) and `.raw`, the full
   `netlab inspect` dictionary for the node. <!-- trace: neops_remote_lab/models/lab.py:23 -->

---

## 5. Run the test

Run pytest the way you normally would:

```bash
pytest tests/test_demo.py -v
```

!!! success "Expected output (abbreviated)"
    ```
    tests/test_demo.py::test_demo_lab_has_two_devices
    [INFO] Connecting to remote lab at: http://lab.example.com:8000
    [INFO] Created session 4b8c... at queue position 0
    [INFO] Session 4b8c... is active after 0.3s.
    [INFO] Starting lab acquisition for demo.yml (reuse=False)
    [INFO] Lab acquired successfully.
    [INFO] Lab acquisition complete: 2 devices
    PASSED
    [INFO] Releasing remote lab for demo.yml
    ```

When the test finishes the fixture's teardown path calls `release()` on the
session client; the server decrements the reference count on the lab and, if
nothing else holds it, tears the topology down. <!-- trace: neops_remote_lab/testing/fixture.py:124 -->

---

## What just happened

Five things, in order:

1. **pytest loaded the plugin.** `neops_remote_lab.testing.pytest_order_plugin`
   registered the `remote_lab_fixture` factory and installed the
   collection-time guard that rejects tests with more than one lab fixture.
2. **The `remote_lab_client` session-scoped fixture connected.** It read
   `REMOTE_LAB_URL`, created a session on the server, and waited for the
   session to reach ACTIVE state — joining a FIFO queue if someone else held
   the host.
3. **Your test asked for `demo_lab`.** The generated fixture uploaded
   `demo.yml` via multipart POST to `/lab`, polling every five seconds if the
   server responded `423 Locked` (another test in the run holding the host).
4. **Netlab brought the topology up.** The server returned a list of
   `DeviceInfoDto` objects once `netlab up` completed. Your test body ran
   against those.
5. **Teardown ran.** The fixture called `release()`, which on a non-reuse lab
   triggers teardown when the reference count hits zero. The session stays
   alive until the pytest process exits — `atexit` cleanup then closes it.

For the full picture of the session queue, heartbeat timeouts, and the
reference-counted lab lifecycle, read [Architecture](../10-concepts/10-architecture.md),
[Session queue](../10-concepts/20-session-queue.md), and [Lab lifecycle](../10-concepts/30-lab-lifecycle.md) in
that order.

---

## Where to go from here

- **Multi-test sharing** — set `reuse_lab=True` on the factory to share one
  running lab across every test that uses the same topology. See the
  `reuse_lab` parameter in [pytest fixtures](../20-client/10-pytest-fixtures.md).
- **Authoring topologies** — vendor defaults, `extra_files`, the `.yml`
  constraint, and common traps are in [Topology format](../10-concepts/40-topology-format.md).
- **Driving the server from Python without pytest** — the client class is
  documented in [RemoteLabClient reference](../20-client/20-python-client.md).
- **Stable public API** — `remote_lab_fixture` is the stable contract
  consumed directly by `neops-worker-sdk-py`. Its signature and semantics
  will not break within a major version.

!!! warning "Authentication is not enforced"
    The server does not validate Bearer tokens — `X-Session-ID` of an active
    session is the only access boundary on `/lab/*` endpoints. Treat the
    Remote Lab Manager as internal-trust infrastructure behind your VPN.
