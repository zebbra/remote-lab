# Remote Lab Manager

Run Netlab topologies on a **remote host** while keeping your pytest suite local.
The service exposes a small REST API that schedules *exclusive* sessions in a
FIFO queue so your CI jobs or multiple developers can share the same
infrastructure safely.

---

## 📦 Installation

Remote Lab Manager is available on PyPI as [`neops_remote_lab`](https://pypi.org/project/neops_remote_lab). You can install it using pip:

```bash
pip install neops-remote-lab
```

You can also install it using Poetry:
```bash
poetry add neops-remote-lab
```



## ✨ Key Points

* **One-lab rule** – only one Netlab topology may run per host; the manager
  enforces this with a queue and automatic reference counting.
* **Zero-config client** – set a single environment variable and your existing
  fixtures will transparently switch to remote mode.
* **Stateless HTTP API** – every request is authenticated via an `X-Session-ID`
  header issued when the session is created.
* **Python client available** – import  RemoteLabClient` for programmatic use.
---

## 🔧 Prerequisites
The Remote Lab Manager requires two main components to function properly:

1. **Netlab** – for orchestrating network topologies on the remote host
2. **VPN connectivity** – to route traffic between your local machine and lab subnets

### Netlab
The Remote Lab Manager orchestrates your topologies with **Netlab** (Containerlab/libvirt + Ansible). Install Netlab on the Remote Lab VM and validate the setup before running tests. Our guide configures rootless Containerlab so you can operate without `sudo` – ideal for CI and automation.

Quick validation:
```bash
netlab test clab
```

See [Netlab Installation & Rootless Containerlab](./docs/netlab_configuration.md) for step‑by‑step instructions and troubleshooting.

### Headscale and Tailscale
Use **Headscale (control plane) with Tailscale clients** to route traffic between your local machine/CI and the lab subnets. You can also bring your own VPN (e.g., WireGuard); the only requirement is that your test runner can reach the lab subnet(s). Headscale/Headplane may run on the Remote Lab VM or any reachable host.

See [Headscale + Headplane with Docker Compose](./docs/headscale_headplane.md) for deployment, access, and client enrollment.


## 🚀 Quick-Start

### On your Remote Lab VM
#### 1. Configure Headscale and Tailscale OR your own VPN solution (e.g. WireGuard)
In order to connect to the Remote Lab subnet(s) from your local machine, you need to configure a VPN solution.

See [Headscale + Headplane with Docker Compose](./docs/headscale_headplane.md) for more details.

#### 2. Start the Remote Lab Server

For local development, you can use the following commands to start the Remote Lab Server:
****
```bash
# Install deps (inside a venv)
poetry install  # includes FastAPI, Uvicorn, etc.

# Run the service
poetry run neops-remote-lab --host 0.0.0.0 --port 8000 --log-level info
```

You can also install the remote lab server from **PyPI**:
```bash
# Install from pypi
pip install neops-remote-lab

# Run the service
neops-remote-lab --host 0.0.0.0 --port 8000 --log-level info
```


### On your Local Machine
#### 1. Setup your local machine to connect to the Remote Lab subnet(s)
Your network needs to be able to reach the Remote Lab subnet(s). After you configured Headscale on your Remote Lab VM, you can connect to it from your local machine.

See [Headscale + Headplane with Docker Compose](./docs/headscale_headplane.md) for more details.

#### 2. Configure Your Tests (in your project)
In projects that use `neops-remote-lab`, set the Remote Lab Manager URL:

```bash
export REMOTE_LAB_URL=http://<host>:8000

# Hetzner neops-labs VM:
export REMOTE_LAB_URL=http://91.99.184.46:8000 

# Optional: put this into a .env file and load it using python-dotenv or your preferred method
```

Additionally, you can also set the following environment variables to override the default timeouts:

| Variable | Description | Default |
|----------|-------------|---------|
| `REMOTE_LAB_REQUEST_TIMEOUT` | Per-request timeout in seconds | 30 |
| `REMOTE_LAB_SESSION_TIMEOUT` | Session heartbeat timeout in seconds | 300 |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | Max seconds to wait for lab acquisition | 600 |


After setting **at least** the `REMOTE_LAB_URL` environment variable, you can then use the fixtures provided by `neops-remote-lab`.

***Example: Define and use a lab fixture***

Declare a fixture for your topology using the provided factory (e.g., `tests/conftest.py`) and use it in your tests (e.g., `tests/function_block_test.py`).

```python
from neops_remote_lab.testing.fixture import remote_lab_fixture

# Declare a fixture for your topology file. Set reuse_lab=True to share the same
# lab across multiple tests in the module (reference-counted on the server).
frr_lab = remote_lab_fixture(
    "tests/topologies/simple_frr.yml",
    reuse_lab=True,
)
```

> **Notes:**
> - The package registers a pytest plugin, so `remote_lab_fixture` can be imported directly as shown.
> - The `REMOTE_LAB_URL` environment variable must be set; the session-scoped `remote_lab_client` fixture will fail fast if it is not.


#### 3. Run pytest as usual (in your project)

```bash
# Run your tests (example paths)
pytest -q
pytest tests/  # or any subset, markers, etc.
```

If `REMOTE_LAB_URL` is set, the fixtures will connect to the configured Remote Lab server and manage the lifecycle of your Netlab topology for each test.

---

## 🔌 REST API

| Method & Path | Purpose | Notes |
|--------------|---------|-------|
| **POST** `/session` | Create a new queue entry | Returns `201` with `session_id` & current `position` |
| **GET** `/session/{id}` | Poll session state | `status: waiting/active`, queue `position` |
| **GET** `/active-session` | Get active session details | Returns `200` with `session_id`, `status` and `position` |
| **DELETE** `/session/{id}` | End a session prematurely | Frees lab if active, returns `204` |
| **POST** `/session/heartbeat` | Keep-alive | Must include `X-Session-ID` header, returns `204` |
| **POST** `/lab` | Upload topology & acquire lab | `multipart/form-data`; `reuse=true|false`; supports repeated `extra_files=@path` |
| **GET** `/lab` | Lab status & device list | Only valid for *active* sessions |
| **GET** `/lab/devices` | Shortcut to device list | – |
| **POST** `/lab/release` | Decrement ref-count | If it drops to zero the lab becomes *idle* |
| **DELETE** `/lab?force=true` | Destroy lab | `202` accepted; `force=false` fails if busy |
| **GET** `/healthz` | Liveness check | `204 No Content` |

> ⚠️ All `/lab*` endpoints require the `X-Session-ID` header of an
> **active** session. Non-active sessions receive `423 Locked`.

> ℹ️ A debug-only endpoint `GET /debug/health` returns rich server stats
> (uptime, queue length, etc.) and is useful during development.

---

## 🛠️  Example cURL Session

```bash
# 1) Create session
SESSION=$(curl -s -X POST http://localhost:8000/session | jq -r .session_id)

# 2) Wait until it becomes ACTIVE (simplified polling)
while true; do
  STATUS=$(curl -s http://localhost:8000/session/$SESSION | jq -r .status)
  [[ $STATUS == "active" ]] && break
  sleep 2
done

# 3) Upload topology & acquire lab
curl -X POST http://localhost:8000/lab \
     -H "X-Session-ID: $SESSION" \
     -F "topology=@tests/topologies/simple_frr.yml" \
     -F "reuse=true"
# Optionally attach supporting files (repeatable)
#    -F "extra_files=@path/to/vars.yml" -F "extra_files=@path/to/your_special_config.yml"

# 4) Release when finished
curl -X POST http://localhost:8000/lab/release -H "X-Session-ID: $SESSION"

# 5) End session
curl -X DELETE http://localhost:8000/session/$SESSION
```

---

## ⚙️  Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `REMOTE_LAB_URL` | Base URL used by client and fixtures | – |
| `REMOTE_LAB_REQUEST_TIMEOUT` | Per-request timeout in seconds | 30 |
| `REMOTE_LAB_SESSION_TIMEOUT` | Session heartbeat timeout in seconds | 300 |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | Max seconds to wait for lab acquisition | 600 |

---

## 🧹 House-Keeping & Timeouts

* **Waiting sessions** – dropped after **600 s** without a heartbeat.
* **Active sessions** – deemed stale after **300 s** of silence; the lab is
  cleaned up and the next session in queue is promoted.
* **Cleanup cadence** – adaptive background task: ~5 s when busy, ~15 s with a
  single active session, ~30 s when idle.

Constants are defined in `neops_worker_sdk/testing/remote_lab/server.py`.

---

## 🪵 Logging

The server emits structured logs:
```
2024-05-27 12:34:56 | INFO     | remote-lab-server | sid=24f... topo=simple_frr.yml | Created session
```
Use `--log-level debug` or the `--debug` flag when starting the service to see queue promotions and
Netlab command output. The `--debug` flag also enables streaming of Netlab output via
`NEOPS_NETLAB_STREAM_OUTPUT=1`. You can override logging with `--log-config <yaml>`; see
`neops_worker_sdk/testing/remote_lab/logging_config.yaml` for the default.

---

## 🧪 Tests

- Remote lab API: `tests/testing/remote_lab/test_server.py`
  - Covers queueing/promotion, heartbeats, active-session, acquire/release/destroy, status codes (400/409/423/202/204), device listing, and `extra_files` directory preservation. Uses a stubbed `LabManager`; no Netlab required.
- Fixture selection: `tests/testing/netlab/test_netlab_fixture_logic.py`
  - Verifies `create_netlab_fixture` local vs remote behavior, `REMOTE_LAB_URL` auto-selection, and conversion to `NetlabDevice`.
- Harness: `tests/conftest.py`
  - Loads `.env`, defines example fixtures, and adds handy pytest markers.

```bash
pytest tests/testing/remote_lab/test_server.py
pytest tests/testing/netlab/test_netlab_fixture_logic.py
pytest -m testing # Run all tests with "testing" marker
```

---

## ❓ Troubleshooting

| Symptom | Checklist |
|---------|-----------|
| Server won’t start | `netlab --version`, correct module path |
| Tests hang in queue | Port 8000 reachable? Heartbeats sent? Check server logs |
| Containers unreachable | Using `network_mode: host`? Firewall rules? |
| Lab stuck busy | Someone forgot to release? Use `DELETE /lab?force=true` |

---

## 📚 Interactive Docs

Browse `http://<host>:8000/docs` for an auto-generated, interactive OpenAPI UI
and experiment with the endpoints directly. 
