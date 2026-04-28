# neops-remote-lab

FastAPI service + pytest11 plugin providing exclusive session-based access to Netlab topologies via a FIFO queue. **Consumed by neops-worker-sdk-py**, which imports `remote_lab_fixture` directly — treat that call signature as a stable public API.

Branch from `develop`. CI (`.github/workflows/ci.yml`) runs `make check`. **CI does not install the Netlab CLI**, so server tests use a stubbed `LabManager`; any test that needs real Netlab must be gated accordingly.

## Conventions

- Pydantic 2 request/response models are suffixed `*Dto`; errors are raised as `HTTPException(status.HTTP_*, detail=...)` — no custom exception hierarchy.
- Blocking I/O (subprocess, file ops) called from async handlers must go through `_run_blocking()` in `server.py` so it lands on the thread-pool executor, not the event loop.
- Netlab is only invoked via `neops_remote_lab.netlab.connector.run_netlab()` — never shell out to `netlab` directly.
- `X-Session-ID` propagates session identity on every `/lab/*` request and on `/session/heartbeat`, and is the only access boundary (see Invariants).

## Invariants & Constraints

Load-bearing and usually not obvious from the code:

- **One server instance per host.** A `filelock` guard in `__main__.py` enforces this and logs the conflicting PID/user/host.
- **One lab per host.** Netlab limitation, enforced both process-wide (`LabManager` singleton) and cross-process (`FileLock`). `LabManager.try_acquire()` is non-blocking and returns `None` when busy (used by the server); `LabManager.acquire()` polls and blocks (used by local test fixtures). Using the wrong one from the wrong context will deadlock or busy-spin.
- **Topology identity is the SHA-256 of file content**, never the filename. Two files with different names but identical content are the same topology; `reuse=True` + reference counting lets multiple tests share one lab, which is torn down when refcount drops to zero.
- **Topology files: `.yml` and `.yaml` both accepted** (case-insensitive) at every layer — HTTP upload, `LabManager.prepare_workdir`. Anything else raises `ValueError`.
- **`atexit` is a real teardown path.** `LabManager` registers a silent cleanup with logging disabled (closed-stream errors). Do **not** add async code to the cleanup path — it will deadlock at process exit.
- **Authentication is not implemented.** `REMOTE_LAB_TOKEN` / Bearer auth is commented out in `client.py`; the only access boundary on `/lab/*` endpoints is the `X-Session-ID` header of an active session (non-active sessions receive `423 Locked`). Treat the service as internal-trust.
- **CVE-pinned dependencies.** Several `pyproject.toml` pins carry `# CVE-*` comments. Preserve them on dep upgrades and re-run `make audit`.
- **`pytest_order_plugin` rejects any test that requests more than one `remote_lab_fixture`** — tests with two lab fixtures fail at collection, not at runtime.
