# Topology File & Netlab Rules

## Topology Files
- Topology files MUST use `.yml` extension (LabManager enforces this)
- Identity is SHA-256 of file content, never the filename -- two files with different names but identical content are the same topology
- When uploading via the API, topology is sent as `multipart/form-data` with field name `topology`

## Netlab CLI Interaction
- All netlab commands run via `neops_remote_lab.netlab.connector.run_netlab()` -- never call netlab directly from server code
- `inspect_node()` returns YAML, `list_nodes()` parses JSON via `ast.literal_eval` (not `json.loads`)
- Streaming output is controlled by `NEOPS_NETLAB_STREAM_OUTPUT=1` env var
- Netlab operations are blocking -- the server runs them in a thread pool via `loop.run_in_executor`

## One-Lab Constraint
- Only one Netlab topology may run per host at any time (Netlab limitation)
- Enforced at two levels: process-wide (`LabManager` singleton) and cross-process (`FileLock` on `{tempdir}/netlab_pytest.lock`)
- `try_acquire()` returns None when busy (non-blocking, used by server)
- `acquire()` polls with 2-second intervals (blocking, used by local test fixtures)
- LabManager registers an `atexit` handler for cleanup -- logging is intentionally disabled during atexit to avoid closed-stream errors
