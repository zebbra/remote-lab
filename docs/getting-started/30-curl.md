---
title: REST quickstart (cURL)
description: Drive a Remote Lab session end-to-end with cURL — create, wait, acquire, inspect, release, delete. The cURL-first onramp for any HTTP-capable stack.
tags: [tutorial, api, getting-started]
crosslink_defines: []
crosslink_references: []
---

# REST quickstart (cURL)

*Drive a Remote Lab session end-to-end with cURL — six calls, any HTTP-capable stack, no Python required.*

You came from a SwiNOG talk, a README, or a colleague who said *"yes, you can drive it from anything"*. This page is for you if you want exclusive access to a real Netlab topology from whatever harness you run — not necessarily Python, not necessarily pytest. Six cURL calls end-to-end.

```bash
export BASE_URL="http://lab.example.com:8000"   # your Remote Lab Manager
curl -fsS "$BASE_URL/healthz" -o /dev/null -w "%{http_code}\n"
```

!!! success "Expected output"
    ```
    204
    ```

A `204 No Content` on `/healthz` is the liveness signal. Anything else — a connection error, a `502`, a redirect — means your VPN is not up or the server is not running. Fix that first; the rest of this page assumes the healthz check passed.

!!! info "Before you start"
    - **A reachable Remote Lab Manager** — `BASE_URL` above. If you are running it locally, that is `http://localhost:8000` (see [Local development server](20-local.md)).
    - **`curl`** and **`jq`** on your `PATH`. `apt install jq` / `brew install jq`.
    - **VPN connectivity to the lab host.** The service has no HTTP authentication — see [Security model](../30-server/30-security.md).

!!! tip "Wrong page?"
    On a Python path? The pytest-flavored [Quickstart](10-pytest.md) is shorter. Wiring this into CI? See [CI quickstart](40-ci.md).

The lifecycle, top-to-bottom: **create a session → wait for the queue → upload a topology → list devices → release → end the session.** The pytest fixture and `RemoteLabClient` automate exactly these six calls.

---

## Create a topology file

Remote Lab uses [Netlab](https://netlab.tools/) topologies to describe
the network. The minimum useful one is two FRR routers on a point-to-point
link with OSPF — small enough to boot in seconds, real enough to exercise
a routing protocol. For the full contract (`provider`, modules, device
kinds, `extra_files`) see [Topology format](../10-concepts/40-topology-format.md).

```yaml title="simple_frr.yml"
provider: clab
defaults.device: frr
module: [ ospf ]
nodes: [ r1, r2 ]
links: [ r1-r2 ]
```

Save this somewhere convenient — you will reference it by path in the
upload step.

!!! tip "`.yml` or `.yaml` — either works"
    Both extensions are accepted (case-insensitive). Pick whichever your
    project already uses; the server normalises behaviour around both.

---

## Step 1 — Create a session

Every interaction begins with `POST /session`. The server appends a new
session to the FIFO queue and returns its UUID and queue position.

```bash
curl -s -X POST "$BASE_URL/session" | jq .
```

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "position": 0
}
```

`position: 0` means the queue was empty and your session is already
`ACTIVE`. Anything higher means you are waiting behind that many other
sessions; poll until promotion (Step 2).

Capture the ID for the rest of the walkthrough:

```bash
SESSION=$(curl -s -X POST "$BASE_URL/session" | jq -r .session_id)
echo "$SESSION"
```

!!! info "Why a session and not just a request?"
    The server only runs one lab at a time. The session is the unit of
    queueing — your session reserves your slot in line, and the
    `X-Session-ID` header is what gates `/lab/*` later. See
    [Session queue](../10-concepts/20-session-queue.md) for the full
    state machine.

---

## Step 2 — Wait until ACTIVE

If your session started at position 0, you can skip this step. Otherwise
poll `GET /session/{id}` until status flips to `active`:

```bash
while true; do
  STATUS=$(curl -s "$BASE_URL/session/$SESSION" | jq -r .status)
  [[ "$STATUS" == "active" ]] && break
  echo "waiting (status=$STATUS)..."
  sleep 2
done
echo "session active"
```

The poll itself counts as activity — `GET /session/{id}` updates the
session's `last_seen_at` timestamp, so a polling waiter does not go
stale. If you walk away mid-wait without polling and without
[heartbeating](../10-concepts/20-session-queue.md#the-heartbeat) for
600 seconds, the server evicts your waiting session and you lose your
slot.

!!! tip "There is a polling script in the repo"
    [`examples/curl/poll_until_active.sh`](https://github.com/zebbra/remote-lab/blob/develop/examples/curl/poll_until_active.sh)
    is the same loop with a few niceties (timeout, structured output).
    Drop it into your CI as-is.

---

## Step 3 — Upload the topology and acquire the lab

With an active session, `POST /lab` to upload your topology and acquire
the lab. The server saves the file to a temp directory, hashes it, and
calls `netlab up`. **This call can take several minutes** while
Containerlab pulls images and Netlab boots the nodes — give it a long
timeout.

```bash
curl -s -X POST "$BASE_URL/lab" \
  -H "X-Session-ID: $SESSION" \
  -F "topology=@simple_frr.yml" \
  -F "reuse=true" | jq .
```

```json
{
  "reused": false,
  "devices": [
    { "name": "r1", "raw": { "...": "full netlab inspect output" } },
    { "name": "r2", "raw": { "...": "full netlab inspect output" } }
  ]
}
```

The `reused: false` field tells you Netlab booted a fresh topology. If
another session had already brought up the same content with `reuse=true`,
you would see `reused: true` and the lab would be shared via reference
counting — the call returns in milliseconds in that case. See
[Lab lifecycle → Reuse](../10-concepts/30-lab-lifecycle.md#reuse-the-refcount-increments).

!!! warning "Reuse is opt-in, and not always what you want"
    Setting `reuse=true` lets multiple sessions share one running lab —
    cheap, but it also means another caller may attach to the same
    topology and see your device-config mutations. If your test mutates
    state, set `reuse=false` (or just omit the field) and accept the
    cold-start cost.

??? warning "If something goes wrong"
    - **`400 Bad Request`** — the topology file is missing or its
      filename does not end in `.yml` / `.yaml`. Check the path you
      passed to `-F "topology=@..."`.
    - **`423 Locked`** — your session is not `ACTIVE` (still waiting), or
      the host is busy with a different topology. Check
      `GET /session/{id}`; if `WAITING`, wait; if `ACTIVE`, see
      [Debugging → HTTP error codes](../30-server/50-debugging.md#common-http-error-codes).
    - **Timeout on the client side** — large topologies legitimately
      take minutes. Set a longer `--max-time` on `curl` and check
      `/debug/health` for queue state.

    Full reference:
    [Debugging](../30-server/50-debugging.md).

---

## Step 4 — Inspect the running devices

Once the lab is up, query the device list any time:

```bash
curl -s "$BASE_URL/lab/devices" -H "X-Session-ID: $SESSION" | jq '.[].name'
```

```
"r1"
"r2"
```

Each device's `raw` field contains the full `netlab inspect` output for
that node — management IP, interface details, the hooks your automation
needs to actually drive the device. The shape is whatever Netlab
produces; the docs deliberately do not pin a schema, since it changes
across Netlab versions.

This is also the cheapest way to keep an active session alive — the
`/lab/*` endpoints all update `last_seen_at` when called.

---

## Step 5 — Release the lab

When you are done, decrement the reference count:

```bash
curl -s -X POST "$BASE_URL/lab/release" \
  -H "X-Session-ID: $SESSION" \
  -w "%{http_code}\n"
```

```
204
```

Release does **not** tear the lab down — it just decrements the
counter. The lab becomes "idle": still running, still responsive, but
unowned. The next acquire decides its fate (reuse, restart, switch, or
eventual cleanup on session timeout). See
[Lab lifecycle → Release](../10-concepts/30-lab-lifecycle.md#release-the-refcount-decrements).

---

## Step 6 — End the session

`DELETE /session/{id}` removes the session from the queue and triggers
`LabManager.cleanup` if your session was holding the lab. The next
waiting session is promoted.

```bash
curl -s -X DELETE "$BASE_URL/session/$SESSION" \
  -w "%{http_code}\n"
```

```
204
```

You do not have to send `X-Session-ID` here — anyone with the session ID
can end it.

---

## The whole thing as one script

`examples/curl/end_to_end_session.sh` ships in the repo and is the
canonical reference — drop it into your CI as-is:

```bash title="examples/curl/end_to_end_session.sh"
--8<-- "examples/curl/end_to_end_session.sh"
```

Run it against your server:

```bash
BASE_URL=http://lab.example.com:8000 \
  examples/curl/end_to_end_session.sh simple_frr.yml
```

---

## From other languages

The REST surface is the universal one. Anything that speaks HTTP can
drive Remote Lab; the Python client and pytest fixture are convenience
layers over exactly this lifecycle. Two short sketches:

=== "Python (no pytest)"

    Use the bundled [`RemoteLabClient`](../20-client/20-python-client.md) — it wraps the six calls above with retries, heartbeating, and timeout coordination. Or see [Cookbook → Python recipes](../99-appendix/cookbook.md#python-no-pytest-recipes) for runnable examples.

=== "Go"

    ```go
    sid := mustPostJSON("/session")["session_id"].(string)
    for mustGetJSON("/session/"+sid)["status"] != "active" {
        time.Sleep(2 * time.Second)
    }
    mustUploadMultipart("/lab", sid, "simple_frr.yml", map[string]string{"reuse": "true"})
    // ... drive the devices ...
    mustPost("/lab/release", sid)
    mustDelete("/session/" + sid)
    ```

    Anything that wraps Go's `net/http` with multipart upload helpers
    will fit. Don't forget to send the `X-Session-ID` header on every
    `/lab/*` call.

=== "Anything else"

    Robot Framework, shell + `curl`, Ansible's `uri` module — they all
    fit. The contract is six requests, the access boundary is the
    `X-Session-ID` header on `/lab/*`, and the only client-side state
    you have to manage is the session UUID and (for long-running
    consumers) a periodic [heartbeat](../10-concepts/20-session-queue.md#the-heartbeat).

---

## Where to go next

- **[CI quickstart](40-ci.md)** — wire this
  lifecycle into GitHub Actions, GitLab CI, or Jenkins. Threads out to
  the queue-contention math for sizing concurrency against a single lab
  host.
- **[REST API](../30-server/40-rest-api.md)** — the authoritative
  endpoint reference: every status code, every response DTO, every
  edge case `/debug/health` and `/active-session` cover.
- **[Debugging](../30-server/50-debugging.md)** — the page to grep when
  something breaks. Symptom/cause/fix table, HTTP error codes, log
  patterns, stale-state recovery.
- **[Session queue](../10-concepts/20-session-queue.md)** and
  **[Lab lifecycle](../10-concepts/30-lab-lifecycle.md)** — the state
  machines behind what you just did. Read these before sizing
  timeouts or building anything that holds a session for tens of
  minutes.
- **[Glossary](../99-appendix/glossary.md)** — every term used above,
  cross-linked back to its in-depth page.
