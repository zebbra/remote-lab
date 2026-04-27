---
title: Quickstart
description: From zero to a passing lab-backed pytest in ten minutes — install, configure, and run your first test against a Remote Lab.
tags: [tutorial, testing, client]
crosslink_defines: []
crosslink_references: []
---

# Quickstart

A pytest suite, a real Netlab topology, three lines of test code. By the end of this page: client installed, `REMOTE_LAB_URL` pointed at a server, a minimal topology booted, a test passing.

!!! tip "Wrong page?"
    Don't have a Remote Lab Manager to point at? [Local development server](20-local.md) installs Netlab + Containerlab rootless on Ubuntu and starts a server on `localhost:8000` — finish that and come back. Driving from a non-Python stack? See the [REST quickstart](30-curl.md). Wiring this into CI? See the [CI quickstart](40-ci.md).

---

## 1. Install the client package

!!! info "Before you start"
    Ubuntu 22.04+ (or similar) with Python 3.11+ and `pipx` available; `pytest` already in your project's virtualenv; a reachable Remote Lab Manager (its base URL is `REMOTE_LAB_URL` in step 2).

Install `neops-remote-lab` into the same environment as your tests. The package ships both the pytest plugin and the HTTP client; no separate install is needed.

=== "uv (recommended)"

    ```bash
    uv add neops-remote-lab
    ```

    Adds the package to your `pyproject.toml` and locks it in `uv.lock`. See the [uv docs](https://docs.astral.sh/uv/concepts/projects/dependencies/) for project workflows.

=== "Poetry"

    ```bash
    poetry add neops-remote-lab
    ```

    Adds the package to your `pyproject.toml` `[tool.poetry.dependencies]` and locks it in `poetry.lock`.

=== "pip"

    ```bash
    pip install neops-remote-lab
    ```

    Installs into the active virtualenv. Pin in `requirements.txt` for reproducibility.

Verify the package and fixture import cleanly:

```bash
python -c "from neops_remote_lab.testing.fixture import remote_lab_fixture; print('OK')"
```

!!! success "Expected output"
    ```
    Successfully installed neops-remote-lab-<version>
    OK
    ```

A successful import means the pytest plugin's entry point is registered (the package's `[project.entry-points.pytest11]` declares `neops-remote-lab` → `neops_remote_lab.pytest_plugins`) and `remote_lab_fixture` is reachable from your test code.

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

The topology is a Netlab YAML file — either `.yml` or `.yaml`,
case-insensitive. We use `.yml` in our examples for consistency, but pick
whichever your project already uses.

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

Curious what just happened? [Runtime walk-through](../10-concepts/10-architecture.md#runtime-walk-through-what-happens-during-a-test) animates the components against this exact test.

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
  consumed directly by the [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/).
  Its signature and semantics will not break within a major version.

!!! danger "No HTTP authentication"
    `neops-remote-lab` ships **without** bearer-token, OAuth, or mTLS
    authentication. The only access boundary on `/lab/*` is the
    `X-Session-ID` of an ACTIVE session. **Deploy behind a VPN.** See
    [Security model](../30-server/40-security.md) for the full posture.
