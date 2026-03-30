# neops-remote-lab

FastAPI service that manages exclusive access to virtual network lab environments for integration testing. Provides a session-based FIFO queue where consumers (typically pytest suites in neops-worker-sdk-py) acquire exclusive access to Netlab-managed network topologies. Also ships as a pytest plugin for automatic topology provisioning in test suites.

Tech: Python 3.12+, FastAPI, Pydantic 2, uvicorn, Netlab CLI, filelock, requests, hatchling + hatch-vcs

## Development

```bash
uv sync

# Run all checks (lint + type check + audit + test)
make check

# Individual targets
make lint        # ruff format --check + ruff check
make format      # ruff format + ruff check --fix
make typeCheck   # pyrefly check
make test        # pytest
make audit       # pip-audit --strict

# Start the server locally (requires netlab CLI in PATH)
uv run neops-remote-lab --debug --port 8000
```

## Conventions

- Linter: ruff with 18 rule sets, line length 120, Google-style docstrings
- Type checker: pyrefly (strict mode, unannotated return/parameter errors enabled)
- Build: hatchling + hatch-vcs (version derived from git tags)
- All env vars use `REMOTE_LAB_` or `NEOPS_NETLAB_` prefix
- Session identity propagated via `X-Session-ID` HTTP header on all lab endpoints
- Topology identity is content-hash (SHA-256), never filename

## Gotchas & Boundaries

- NEVER run more than one server instance per host -- a `filelock` guard prevents it and logs the conflicting PID
- NEVER assume topology identity from filename -- `LabManager` compares SHA-256 of file content, not paths
- ALWAYS use `.yml` extension for topology files -- the server accepts `.yml` and `.yaml` but `LabManager` enforces `.yml`
- ALWAYS handle `atexit` cleanup -- `LabManager` registers an `atexit` handler that silently tears down running labs (logging disabled to avoid closed-stream errors)
- One lab at a time per host -- this is a Netlab limitation enforced at both process and cross-process (filelock) levels
- Startup cleanup tears down any stale "default" Netlab instance as a safety net for CI runners
- `REMOTE_LAB_TOKEN` / Bearer auth is commented out in `client.py` -- planned but not active

## Session Queue Model

```
POST /session      -> Create session (WAITING or promoted to ACTIVE if queue empty)
GET /session/:id   -> Poll status + position in queue
DELETE /session/:id -> End session, promote next in queue, cleanup lab
POST /session/heartbeat -> Keep-alive (X-Session-ID header required)
```

- First session in queue is ACTIVE; all others are WAITING
- Waiting sessions timeout after 600s; active sessions without heartbeat timeout after 300s
- Background cleanup runs at adaptive intervals: 30s idle, 15s one session, 5s multiple sessions

## Content-Hash Reuse

The `LabManager` identifies topologies by SHA-256 hash of file content:
- Two different file paths with identical content are treated as the same topology
- Reference counting allows multiple tests to share one topology via `reuse=True`
- `try_acquire()` is non-blocking (returns None when busy) -- used by the server
- `acquire()` polls with 2s intervals -- used by local test fixtures

## Ecosystem Context

- **Depends on**: neops-workflow-engine (shares `neops-workflow-engine-client` dependency)
- **Consumed by**: neops-worker-sdk-py (pytest fixtures via `remote_lab_fixture()` factory, auto-registered as pytest11 plugin)
- **External tool**: Netlab CLI must be installed and in PATH (verified at server startup)

## Key Configuration

| Variable | Default | Purpose |
|---|---|---|
| `REMOTE_LAB_URL` | (unset = local mode) | Base URL of remote lab server |
| `REMOTE_LAB_REQUEST_TIMEOUT` | 30 | HTTP request timeout in seconds |
| `REMOTE_LAB_SESSION_TIMEOUT` | 600 | Session queue wait timeout in seconds |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | 600 | Lab acquisition timeout in seconds |
| `NEOPS_NETLAB_STREAM_OUTPUT` | (unset) | Set to "1" to stream netlab output to console |
