---
title: CI integration
description: Wire Remote Lab into GitHub Actions, GitLab CI, or Jenkins — environment variables, runner pipeline tabs, queue-contention math, timeout coordination, VPN-runner notes.
tags: [how-to, server, ci, deployment]
crosslink_defines: []
crosslink_references: []
---

# CI integration

Whatever harness you use — pytest in Python, Robot Framework, a shell
pipeline of `curl` calls, your own Go test runner — the integration shape
is the same: set a base URL, run the test command, let the lifecycle
fall out of the session API. This page covers the pieces that change
between *a developer running tests on a laptop* and *a CI fleet running
them under contention*: environment variables, runner pipeline shapes,
the queue-contention math, and the operational tips that come up once
real concurrency lands on a single lab host.

The page is harness-agnostic. Where it shows pytest commands, those are
the canonical Python path; the same env-vars and timeout coordination
apply if you are running `go test`, a Robot Framework suite, or a shell
script of `curl` calls — see the
[REST quickstart](../getting-started/30-rest-quickstart.md) for the
non-Python lifecycle.

---

## Configuring the client environment

The Python client (and therefore the pytest fixture) is driven entirely
by environment variables. There are no CI-platform-specific flags — set
the env, run the test command, the rest is the same on every runner.

```bash
export REMOTE_LAB_URL=http://lab.example.com:8000
```

`REMOTE_LAB_URL` is required for the pytest fixture; the
`remote_lab_client` session fixture raises `RuntimeError` at test setup
if it is missing. <!-- trace: neops_remote_lab/testing/fixture.py:34 -->
For non-Python harnesses, `REMOTE_LAB_URL` is just a convention — your
code reads whatever env var you want and points `curl`/`http.Client` at
it.

For the optional timeout overrides
(`REMOTE_LAB_REQUEST_TIMEOUT`, `REMOTE_LAB_SESSION_TIMEOUT`,
`REMOTE_LAB_ACQUISITION_TIMEOUT`) and the canonical defaults table, see
[Configuration → Optional: the three timeout variables](20-configuration.md#optional-the-three-timeout-variables).
The short version, with CI-relevant guidance:

| Variable | When to raise it |
|---|---|
| `REMOTE_LAB_REQUEST_TIMEOUT` | Individual HTTP requests time out on a slow link. Default 30 s. |
| `REMOTE_LAB_SESSION_TIMEOUT` | Queue waits regularly exceed 10 minutes (multiple CI jobs sharing one server). Default 600 s. |
| `REMOTE_LAB_ACQUISITION_TIMEOUT` | Large topologies where `netlab up` takes more than 10 minutes. Default 600 s. |

!!! warning "Client and server session timeouts must agree"
    The server independently evicts stale sessions —
    `_WAITING_SESSION_TIMEOUT` is 600 s and `_ACTIVE_SESSION_STALE` is
    300 s. <!-- trace: neops_remote_lab/server.py:95 --> If your client
    `REMOTE_LAB_SESSION_TIMEOUT` is longer than 600 s, the server will
    drop your waiting session before the client gives up — your CI sees
    a confusing timeout error. Coordinate with the operator before
    raising client-side timeouts past the server defaults. See
    [Configuration → Server environment variables](20-configuration.md#server-environment-variables).

---

## Session lifecycle (the short version)

The pipeline tabs below assume the client (or your shell script) walks
the same four-step lifecycle the
[REST quickstart](../getting-started/30-rest-quickstart.md) covers:

1. **Create session** — `POST /session` returns a `session_id` and queue
   position.
2. **Wait for ACTIVE** — poll `GET /session/{id}` every 5 s (the
   `RemoteLabClient` does this on creation).
3. **Acquire lab** — `POST /lab` uploads the topology and blocks until
   ready. On `423 Locked` (lab busy with another topology) the client
   sleeps 5 s and retries.
4. **Release + close** — `POST /lab/release` decrements the refcount;
   `DELETE /session/{id}` ends the session and (if the lab was held by
   this session) triggers cleanup.

For the underlying state machines see
[Session queue](../10-concepts/20-session-queue.md) and
[Lab lifecycle](../10-concepts/30-lab-lifecycle.md).

---

## Topology upload

`POST /lab` accepts the topology as a `multipart/form-data` field. The
server saves the bytes to a temp directory, computes the SHA-256 of the
content, and runs `netlab up`. **Two files with different filenames but
identical content are the same topology** — when `reuse=true` is set,
the second upload attaches to the running lab via reference counting
instead of restarting it. See
[Lab lifecycle → Topology identity](../10-concepts/30-lab-lifecycle.md#topology-identity-is-content-not-filename).

---

## Test execution ordering for pytest users

The pytest plugin groups tests by their `remote_lab_fixture` so all
tests sharing a topology run consecutively. This minimises Netlab
teardown/restart cycles on the server. To see the computed order, run
with log output:

```bash
pytest -s --log-cli-level=INFO
```

The plugin logs a structured table showing fixture groups, topology
paths, and test order. Full reference:
[Pytest fixtures → Test execution ordering](../20-client/10-pytest-fixtures.md#test-execution-ordering).

This optimisation does not apply to non-pytest harnesses; if you are
driving the lab from a shell loop or a Go test runner, group your test
order yourself or set `reuse=true` and pay the refcount cost rather than
the restart cost.

---

## HTTP retry behaviour

`RemoteLabClient` configures automatic retries for transient failures:

- Retries up to **3 times** on status codes `429`, `500`, `502`, `503`,
  `504`.
- Exponential backoff (factor of 1 second).
- Only retries safe methods (`GET`, `HEAD`, `OPTIONS`, `DELETE`) — `POST`
  is **not** retried automatically, to avoid duplicate side effects.
- When `POST /lab` returns `423 Locked` (lab busy with another
  topology), the client retries in a 5-second loop until the lab
  becomes available, bounded by `REMOTE_LAB_ACQUISITION_TIMEOUT`.

If you are writing a non-Python client, replicate at least the
`POST /lab` 423-retry loop — that is the contract `try_acquire` sets up
on the server side.

---

## CI integration

Three runner-by-runner sketches. The shape is identical: set the env,
run the test command. Replace `pytest tests/ -q` with whatever your
test command actually is.

=== "GitHub Actions"

    ```yaml title=".github/workflows/integration.yml"
    - name: Run integration tests
      env:
        REMOTE_LAB_URL: http://lab.example.com:8000
        REMOTE_LAB_SESSION_TIMEOUT: "1200"
      run: pytest tests/ -q
    ```

=== "GitLab CI"

    ```yaml title=".gitlab-ci.yml"
    integration-tests:
      stage: test
      image: python:3.12
      variables:
        REMOTE_LAB_URL: "http://lab.example.com:8000"
        REMOTE_LAB_SESSION_TIMEOUT: "1200"
      script:
        - pip install -e .[test]
        - pytest tests/ -q
      # GitLab-level timeout; coordinates with REMOTE_LAB_SESSION_TIMEOUT
      timeout: 30 minutes
    ```

    If your runner is not on the Tailscale mesh, add a pre-`script`
    step to `tailscale up --auth-key "$TAILSCALE_AUTHKEY"` before the
    test command. See
    [Headscale VPN](../40-deployment/20-headscale-vpn.md).

=== "Jenkins (declarative)"

    ```groovy title="Jenkinsfile"
    pipeline {
        agent { label 'tailnet-runner' }
        environment {
            REMOTE_LAB_URL              = 'http://lab.example.com:8000'
            REMOTE_LAB_SESSION_TIMEOUT  = '1200'
        }
        options {
            timeout(time: 30, unit: 'MINUTES')
        }
        stages {
            stage('Integration tests') {
                steps {
                    sh 'pip install -e .[test]'
                    sh 'pytest tests/ -q'
                }
            }
        }
    }
    ```

    Pin the agent label (`tailnet-runner` above) to whichever Jenkins
    executor pool has VPN access to the lab server.

---

## Tips for CI

- **VPN connectivity.** The CI runner must reach the Remote Lab server
  and the lab subnet — there is no HTTP authentication, so the network
  boundary is the access boundary. If you use Headscale/Tailscale,
  ensure the runner has a valid tailnet session before the test
  command runs. See [Headscale VPN](../40-deployment/20-headscale-vpn.md).
- **Parallel jobs.** Multiple CI jobs can target the same server — the
  session queue serializes access. Raise `REMOTE_LAB_SESSION_TIMEOUT`
  on the client to accommodate queue depth, and coordinate with the
  server-side `_WAITING_SESSION_TIMEOUT`.
- **Fail fast on bad config.** If `REMOTE_LAB_URL` points at an
  unreachable server, the pytest fixture fails at session creation
  rather than mid-test. You will see a `ConnectionError` in the first
  seconds of the run — useful, since you can fix the env-var without
  burning a 30-minute CI slot.
- **Cleanup on cancellation.** If a CI job is killed mid-run, the
  `atexit` handler attempts to close the session. On `SIGKILL` the
  process cannot run handlers; the server's stale-session cleanup
  reclaims the slot after the heartbeat timeout (default 300 s for
  `ACTIVE`). See
  [Session queue → Stale-session eviction](../10-concepts/20-session-queue.md#stale-session-eviction).
- **Log level.** Set `--log-cli-level=INFO` (pytest) or its equivalent
  in your harness to capture session creation, queue position, and lab
  acquisition events in build logs. This is the difference between
  "the test timed out somewhere" and "the test waited 12 minutes for
  the queue then acquired" when you read failures after the fact.

---

## Queue contention in shared CI

When multiple runners point at one Remote Lab server, each creates its
own session and enters the FIFO queue. The server promotes exactly one
to `ACTIVE` at a time
([Session queue](../10-concepts/20-session-queue.md)); everyone else
waits.

**What each client does while waiting:**

<!-- trace: neops_remote_lab/client.py:197 -->

- On `POST /lab`, if the server returns `423 Locked` (another session
  holds the lab with a different topology), `RemoteLabClient.acquire()`
  sleeps 5 s and retries in a loop. The loop is bounded by
  `lab_acquisition_timeout` (default 600 s /
  `REMOTE_LAB_ACQUISITION_TIMEOUT`); after that the client raises.
- While the session is still `WAITING` in the queue,
  `GET /session/{id}` polls every 5 s until promotion. The poll itself
  refreshes `last_seen_at`, so polling waiters do not go stale.

### Choosing CI concurrency

For `N` concurrent runners all expecting to run tests against one
server, the back-of-envelope queue-depth worst case is:

```
queue_depth_wait ≈ N × (avg_lab_hold_time + teardown_cost)
```

If `avg_lab_hold_time + teardown_cost` is 5 minutes and you run 8
concurrent jobs, the 8th job waits up to ~40 minutes. Compare to the
server's `_WAITING_SESSION_TIMEOUT` (600 s) — if the tail wait exceeds
that, the server drops the session and your client sees a timeout
error. Two ways out:

1. **Lower concurrency** to keep the worst-case wait under
   `_WAITING_SESSION_TIMEOUT`.
2. **Raise both timeouts together** — client
   `REMOTE_LAB_SESSION_TIMEOUT` and server `_WAITING_SESSION_TIMEOUT`
   must agree (the server-side constant is at the moment a code
   change, not a knob; coordinate with the operator).

### Shared topologies collapse the queue

If multiple CI jobs target the **same** topology with `reuse=true`,
they do **not** serialize on `netlab up` — the server reuses the
running lab and acquire becomes a refcount increment. This is the
single biggest contention mitigation. A fleet of 20 tests sharing one
topology pays Netlab boot cost once and queues only at the session
layer (which is much cheaper). See
[Pytest fixtures → reuse_lab](../20-client/10-pytest-fixtures.md)
for the fixture-level switch and
[Lab lifecycle → Reuse](../10-concepts/30-lab-lifecycle.md#reuse-the-refcount-increments)
for the underlying mechanism.

### Per-request timeout, not wall-clock

`REMOTE_LAB_ACQUISITION_TIMEOUT` is passed as the `timeout=` kwarg on
each individual `POST /lab` call (`client.py:192`); it is **not** a
wall-clock bound on the `while True:` 423-retry loop. A loaded server
that returns `423 Locked` quickly will make the client spin forever at
5-second intervals. To fail fast, wrap the acquire in a pytest-level
timeout or use CI-level job timeouts:

```python
# Pytest-level (per test, via pytest-timeout)
# pyproject.toml:
# [tool.pytest.ini_options]
# timeout = 900   # total per-test, including lab acquire + teardown

# Or inline per-test:
@pytest.mark.timeout(900)
def test_with_bounded_wait(simple_lab):
    ...
```

```yaml
# GitHub Actions job-level bound
jobs:
  test:
    timeout-minutes: 20
```

Pair bounded waits with a retry-the-whole-job CI policy so transient
contention does not cause false failures.

---

## Verifying server reachability

Before running your full suite, confirm connectivity from the runner:

```bash
# Liveness check
curl -s -o /dev/null -w "%{http_code}" "$REMOTE_LAB_URL/healthz"
# Expected: 204

# Detailed server status
curl -s "$REMOTE_LAB_URL/debug/health" | jq .
```

If the liveness check fails the server is down or unreachable — fix
that before anything else; the pipeline cannot recover from missing
transport. See
[Debugging](50-debugging.md).

---

## Where to go next

- **[Debugging](50-debugging.md)** — symptom/cause/fix table, HTTP
  error codes, log-pattern tables. The page to grep when a CI run
  fails in a way the build log does not explain.
- **[Configuration](20-configuration.md)** — full reference for every
  client and server environment variable, including the timeout
  defaults this page only summarises.
- **[Session queue](../10-concepts/20-session-queue.md)** — promotion
  rules, stale-session eviction, the 600 s / 300 s timeouts behind the
  contention math above.
- **[Headscale VPN](../40-deployment/20-headscale-vpn.md)** — the
  recommended enclosure for the lab host. Required before any CI
  runner outside the operator's office can reach the server.
