---
page_purpose: tutorial
personas_served: [junior-network-engineer, devops-engineer]
difficulty_level: beginner
---

# Your First Lab Session

This walkthrough takes you through the entire Remote Lab lifecycle using nothing but cURL. By the end you will have created a session, uploaded a topology, inspected the running devices, and cleaned up -- the same steps the Python client and pytest fixtures automate for you.

!!! note "Prerequisites"
    Complete [Setup](10-setup.md) first. You need `REMOTE_LAB_URL` set and the server reachable.

## Create a topology file

Remote Lab uses [Netlab](../99-appendix/glossary.md#netlab) [topology](../99-appendix/glossary.md#topology) files to describe the network you want to spin up. (For the full contract — supported providers, modules, device kinds, and the `extra_files` mechanism — see [Topology Format](../10-concepts/40-topology-format.md).) Create a minimal FRR topology to use throughout this tutorial:

```yaml title="simple_frr.yml"
provider: clab
defaults.device: frr

module: [ ospf ]

nodes: [ r1, r2 ]
links: [ r1-r2 ]
```

This declares two FRR (Free Range Routing) routers connected by a point-to-point link with OSPF enabled. Two Netlab-specific fields are worth naming:

- `defaults.device: frr` -- the **default device kind** applied to every node that does not override it. "Device kind" is Netlab's term for a vendor/image pairing (`frr`, `eos`, `srlinux`, `iol`, etc.); it drives which container image is used and which configuration templates are rendered. See [Topology Format -- Supported device kinds](../10-concepts/40-topology-format.md#supported-device-kinds) for the list.
- `module: [ ospf ]` -- the **Netlab modules** to enable across the topology. A module is a protocol or feature layer (OSPF, BGP, ISIS, VRFs, etc.) that Netlab knows how to configure per device kind. See [Topology Format -- Supported Netlab modules](../10-concepts/40-topology-format.md#supported-netlab-modules).

Under the hood, Netlab transforms this into a Containerlab `clab.yml` and Containerlab brings up the containers; see [Architecture -- Components](../10-concepts/10-architecture.md#components) for the full layering.

Save this file somewhere convenient -- you will reference it by path in the cURL commands below.

## Step 1 -- Create a session

Every interaction with Remote Lab starts by creating a **session**. The session enters a first-in, first-out (FIFO) queue; if nobody else is using the server, it becomes active immediately.

```bash
curl -s -X POST $REMOTE_LAB_URL/session | jq .
```

Expected response:

```json
{
  "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
  "position": 0
}
```

`position: 0` means your session is active right away. If someone else is using the lab, you will get `position: 1` or higher -- poll `GET /session/{id}` (Step 2) to watch the status change to `active`.

Save the session ID for the remaining steps:

```bash
SESSION="a1b2c3d4-e5f6-7890-abcd-ef1234567890"  # use your actual session_id
```

!!! tip "One-liner"
    Capture the session ID directly:
    ```bash
    SESSION=$(curl -s -X POST $REMOTE_LAB_URL/session | jq -r .session_id)
    ```

## Step 2 -- Poll until active

If your session started in the `waiting` state, poll until it becomes `active`:

```bash
curl -s $REMOTE_LAB_URL/session/$SESSION | jq .
```

Response while waiting:

```json
{
  "status": "waiting",
  "position": 1
}
```

Response when active:

```json
{
  "status": "active",
  "position": 0
}
```

A simple polling loop:

```bash
while true; do
  STATUS=$(curl -s $REMOTE_LAB_URL/session/$SESSION | jq -r .status)
  echo "Session status: $STATUS"
  [[ $STATUS == "active" ]] && break
  sleep 2
done
```

If your session was already active (position 0), this loop exits immediately.

## Step 3 -- Upload topology and acquire the lab

With an active session, upload your topology file. The server will run `netlab up` behind the scenes to start the containers.

```bash
curl -s -X POST $REMOTE_LAB_URL/lab \
     -H "X-Session-ID: $SESSION" \
     -F "topology=@simple_frr.yml" \
     -F "reuse=true" | jq .
```

This request may take a minute or more while Netlab brings up the topology. You will know the command worked when the response contains a `devices:` array with one entry per node (`r1`, `r2`) and `reused: false`:

```json
{
  "reused": false,
  "devices": [
    {
      "name": "r1",
      "raw": { "...": "full netlab inspect output" }
    },
    {
      "name": "r2",
      "raw": { "...": "full netlab inspect output" }
    }
  ]
}
```

The `reused: false` field tells you the lab was freshly started. If another session had already brought up the same topology with `reuse=true`, you would see `reused: true` and the lab would be shared via reference counting.

!!! info "What just happened?"
    The server saved your topology to a temp directory, computed a SHA-256 hash of it, and called `netlab up` to start the Containerlab topology. For more detail, see [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md).

??? warning "If something goes wrong"
    - **Connection refused**: The server is not running or not reachable. Check `curl $REMOTE_LAB_URL/healthz` -- you should get HTTP 204.
    - **400 Bad Request**: The topology file is missing or does not have a `.yml`/`.yaml` extension. Double-check the filename and path.
    - **423 Locked**: Your session is not yet active, or another topology is running. Poll your session status and wait.
    - **Timeout**: Large topologies can take several minutes. Try again with a longer timeout, or check server logs for errors.
    - For more, see [Debugging and Troubleshooting](../40-testing/40-debugging.md).

## Step 4 -- Check devices

You can query the running devices at any time:

```bash
curl -s $REMOTE_LAB_URL/lab/devices -H "X-Session-ID: $SESSION" | jq .
```

```json
[
  {
    "name": "r1",
    "raw": { "...": "..." }
  },
  {
    "name": "r2",
    "raw": { "...": "..." }
  }
]
```

The `raw` field contains the full `netlab inspect` output for each node, including management IPs and connection details your tests would use.

## Step 5 -- Release the lab

When you are done with the topology, release it. This decrements the reference count. If no other sessions are holding the lab, it becomes idle and eligible for teardown.

```bash
curl -s -X POST $REMOTE_LAB_URL/lab/release \
     -H "X-Session-ID: $SESSION" -w "\nHTTP %{http_code}\n"
```

```
HTTP 204
```

## Step 6 -- End the session

Finally, close your session. This frees your slot in the queue and lets the next waiting client proceed.

```bash
curl -s -X DELETE $REMOTE_LAB_URL/session/$SESSION -w "\nHTTP %{http_code}\n"
```

```
HTTP 204
```

## Complete script

Here is the entire flow as a single copy-pasteable script:

```bash
#!/usr/bin/env bash
set -euo pipefail

# 1) Create session
SESSION=$(curl -s -X POST $REMOTE_LAB_URL/session | jq -r .session_id)
echo "Created session: $SESSION"

# 2) Wait until active
while true; do
  STATUS=$(curl -s $REMOTE_LAB_URL/session/$SESSION | jq -r .status)
  [[ $STATUS == "active" ]] && break
  echo "Waiting... (status: $STATUS)"
  sleep 2
done
echo "Session is active"

# 3) Upload topology and acquire lab
echo "Acquiring lab (this may take a minute)..."
curl -s -X POST $REMOTE_LAB_URL/lab \
     -H "X-Session-ID: $SESSION" \
     -F "topology=@simple_frr.yml" \
     -F "reuse=true" | jq .

# 4) Check devices
echo "Devices:"
curl -s $REMOTE_LAB_URL/lab/devices -H "X-Session-ID: $SESSION" | jq '.[].name'

# 5) Release lab
curl -s -X POST $REMOTE_LAB_URL/lab/release -H "X-Session-ID: $SESSION"
echo "Lab released"

# 6) End session
curl -s -X DELETE $REMOTE_LAB_URL/session/$SESSION
echo "Session ended"
```

## What to read next

You now understand the full request flow that the Python client automates. Next, head to [Using Pytest Fixtures](30-pytest-fixtures.md) to see how `remote_lab_fixture` wraps all of these steps into a single pytest fixture.

For a deeper understanding of the concepts behind what you just did:

- [Architecture](../10-concepts/10-architecture.md) -- how the client and server components fit together
- [Session Queue](../10-concepts/20-session-queue.md) -- how the FIFO queue serializes access
- [Lab Lifecycle](../10-concepts/30-lab-lifecycle.md) -- what happens during acquire, reuse, and release
