---
title: Invariants
description: The eight hard rules every change in neops-remote-lab must preserve.
tags: [contributing, reference]
crosslink_defines: []
crosslink_references: []
---

# Invariants

*Eight rules a PR cannot violate. Each is short. Re-read the relevant one **before** any non-trivial change to `server.py`, `lab_manager.py`, or `connector.py`.*

A change cannot break any of these without coordinating with every consumer of the surface area. Each entry: what the rule is, **why** it exists, and **what breaks** if it goes away.

The mechanics that *enforce* these rules — `_run_blocking`, the `LabManager` singleton, atexit teardown, the test-stubbing pattern — live in their own pages under [Internals](30-internals-async.md). Before touching `server.py`, `lab_manager.py`, or `netlab/connector.py`, read both this page and the relevant Internals page.

---

## One server instance per host

<!-- trace: neops_remote_lab/__main__.py:104 -->
The entrypoint takes a non-blocking `FileLock` at a fixed path under the system temp directory. A second instance attempting to start on the same host fails the lock, logs the running owner's pid/user/host/bind/cmd, and exits with status 1.

| Why | Two servers would race on the single Netlab `default` instance and corrupt lab state mid-test. |
|---|---|
| What breaks | Concurrent `netlab up`/`netlab down` from two processes; orphaned containers; queue corruption. |

Stale-lock recovery procedure: [Administration → Stale-lock recovery](../30-server/10-administration.md#stale-lock-recovery).

---

## One lab per host

<!-- trace: neops_remote_lab/netlab/lab_manager.py:43 -->
Netlab itself only manages one topology per host. `LabManager` enforces this twice — a class-level singleton in-process, plus a system-wide `FileLock` for cross-process serialization.

| Why | The two layers exist for different threats: the singleton stops two async tasks in the server from racing; the file lock stops a separate Python process (e.g. a developer running local `netlab` by hand alongside the server) from trampling shared state. |
|---|---|
| What breaks | Two callers' lab state collide; one tears down the other's containers mid-test. |

Mechanics: [Internals: LabManager singleton & locking](40-internals-lab-manager.md).

---

## Topology identity is the SHA-256 of file content

<!-- trace: neops_remote_lab/netlab/lab_manager.py:129 -->
Not the filename. Two files with different names but identical bytes are the same topology — `reuse=True` on the second upload attaches to the running lab. Edit one byte and it is a new topology; `reuse=True` will refuse and either teardown-then-restart (if `ref == 0`) or return `423`.

| Why | Most systems key on filename. This one doesn't, so a test helper that copies a vendored topology into each test's workdir still gets reuse for free. |
|---|---|
| What breaks | Code that depends on filename equality is wrong; reuse stops working across copy-paste topologies and CI suddenly pays Netlab boot cost on every test. |

---

## `.yml` and `.yaml` are both accepted

<!-- trace: neops_remote_lab/netlab/lab_manager.py:68 -->
Both extensions, case-insensitive, pass `prepare_workdir`'s suffix check (`.yml`, `.yaml`, `.YML`, `.YAML`). The HTTP layer accepts the same set, so the surface is uniform end-to-end.

| Why | There is no asymmetry between what `POST /lab` validates and what `LabManager` accepts. Consumers shouldn't have to remember which extension this project happens to prefer. |
|---|---|
| What breaks | If you add a new entry point that copies a topology and forgets to mirror this check, callers see "topology accepted, then mysteriously rejected" failures with no clear cause. |

If you add a new entry point that copies a topology, mirror this check (suffix in `(".yml", ".yaml")` after `.lower()`). Anything else — `.json`, `.txt`, no extension — should raise loudly.

---

## `X-Session-ID` is the only access boundary on `/lab/*`

<!-- trace: neops_remote_lab/server.py:390 -->
There is no Bearer token, no mTLS, no tenant header. The `/lab/*` endpoints gate on a header lookup that confirms the session exists and is `ACTIVE`. Non-active sessions get `423 Locked`; unknown sessions get `404`.

`/session/heartbeat` is gated more loosely: it only requires the session to exist (so a `WAITING` session can keep its queue slot alive). This asymmetry is deliberate — see [Session Queue → access boundary](../10-concepts/20-session-queue.md#the-access-boundary).

| Why | The service is internal-trust. Any deployment without a VPN enclosure exposes a lab host to the open internet. |
|---|---|
| What breaks | Adding any other auth path (Bearer, mTLS, header magic) without removing this one creates a confused threat model: callers get to choose which boundary to bypass. |

Full posture: [Security model](../30-server/30-security.md).

---

## `*Dto` suffix on Pydantic request/response models {#dto-suffix}

Every request and response model in `neops_remote_lab.models.*` ends in `Dto`: `SessionInfoDto`, `CreateSessionResponseDto`, `LabStatusDto`, `AcquireResponseDto`, `DeviceInfoDto`. Code review will reject a PR that introduces a model without the suffix.

| Why | The convention lets a reader scan a file and immediately distinguish wire-format models from internal types. |
|---|---|
| What breaks | Mixing them is a recipe for accidentally serializing internal state to the HTTP surface. |

---

## CVE-pinned dependencies {#cve-pinned-dependencies}

Several entries in `pyproject.toml` carry `# CVE-*` comments:

```toml
"starlette>=0.49.1",   # CVE-2025-62727 fix
"filelock>=3.20.1,<4", # CVE-2025-68146 fix
"pytest>=9.0.3,<10",   # CVE-2025-71176 fix
```

When upgrading, preserve the comment and pick a version that still includes the patch. Then re-run `make audit` (`pip-audit --strict`) to confirm.

| Why | The convention is enforced by code review and by `make audit` in CI. It is not enforced by tooling alone — comments can be deleted accidentally — so treat them as load-bearing. |
|---|---|
| What breaks | Deleting a `# CVE-*` comment loses the silent metadata that justifies the pin; the next upgrade may regress a security patch. |

---

## One `remote_lab_fixture` per test (collection-time)

<!-- trace: neops_remote_lab/testing/pytest_order_plugin.py:88 -->
A test that depends on more than one fixture created by `remote_lab_fixture` fails at pytest **collection** with `ValueError`. The plugin walks fixture metadata at collection time, so the failure is immediate.

| Why | A runtime failure (the second `acquire` would loop in the `423` polling path forever, because the first `acquire`'s session still holds the host) is much harder to diagnose than a clear `ValueError` during collection. |
|---|---|
| What breaks | Removing the collection-time check turns a clear error into a silent, several-minute hang. |

If you need to exercise two topologies in the same test process, use `reuse_lab=True` on one and split into two tests. The plugin reorders by fixture rank to keep tests against the same lab contiguous; see [Pytest Fixtures → Test execution ordering](../20-client/10-pytest-fixtures.md#test-execution-ordering).

---

## See also

- **[Anti-patterns](70-anti-patterns.md)** — the consolidated "don't" table that names each invariant by the rule it violates. Grep this when reviewing a PR.
- **[Internals: Async discipline](30-internals-async.md)** — the `_run_blocking` mechanics behind the one-server-per-host invariant.
- **[Internals: LabManager singleton & locking](40-internals-lab-manager.md)** — `try_acquire` vs `acquire`, GLOBAL_LOCK, stale-state recovery — the mechanics behind one-lab-per-host.
- **[Internals: atexit + lifespan](50-internals-atexit.md)** — why teardown stays synchronous and silent.
- **[Internals: CI test stubbing](60-internals-test-stubbing.md)** — how `LabManager` is shaped to make CI tests possible without `netlab`.
- **[`AGENTS.md`](https://github.com/zebbra/neops-remote-lab/blob/develop/AGENTS.md)** — the same invariants in repo-root form, plus the rest of the agent bootstrap context.
