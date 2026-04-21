---
title: Topology Format
description: The Netlab YAML shape neops-remote-lab expects — required .yml extension, provider choice, node/link structure, and the extra_files multipart contract.
tags: [concept, testing, deployment]
crosslink_defines: [topology]
crosslink_references: []
---

# Topology Format

A topology is a single YAML file that tells Netlab what network to build:
which nodes, which links, which provider. `neops-remote-lab` accepts that
file over HTTP, copies it into a clean workdir, and hands it to the Netlab
CLI verbatim. The YAML dialect is Netlab's, not ours — but a handful of
server-side rules make the difference between a topology that queues and one
that 423s you after a five-minute wait.

> **Why cover this here if Netlab owns the schema?** Two reasons. First, the
> `.yml` extension rule and the `extra_files` upload contract are enforced
> in *this* server, not in Netlab. Second, fixture consumers often inherit
> topologies from upstream repos and need a single-page reference for the
> contract they're honouring.

## The minimal topology

A working Netlab topology needs a provider, at least one node, and usually
some links. Here is the smallest useful starting point — two FRR routers on
one link:

```yaml title="minimal_frr.yml"
provider: clab
defaults:
  device: frr

nodes:
  r1:
  r2:

links:
  - r1-r2
```

Expected Netlab output on `netlab up`:

```
Lab default started on provider clab
Nodes: r1, r2
```

??? info "Use placeholder values, not hardcoded IPs"
    If your topology pins management addresses or interface IPs, keep them
    in a site-local range you control and document the substitution
    expected by callers. In any shipped example, use `$LAB_HOST` for the
    server address and RFC 5737 documentation ranges (`192.0.2.0/24`,
    `198.51.100.0/24`, `203.0.113.0/24`) for placeholder device IPs.

## Required: the .yml extension

<!-- trace: neops_remote_lab/netlab/lab_manager.py:68 -->
`prepare_workdir` — the function every acquire flows through — will only
copy a topology whose suffix is `.yml` (lowercase). Any other extension,
including `.yaml`, `.YML`, or `.yml.bak`, raises `ValueError("Topology must
be a .yml file")` and aborts the acquire.

<!-- trace: neops_remote_lab/server.py:404 -->
The `POST /lab` endpoint pre-validates the upload filename against the
looser pattern `{.yml, .yaml}` (case-insensitive), so a `.yaml` file
passes the HTTP validation and then fails inside `LabManager`. Result: the
session is already ACTIVE when the rejection happens, wasting a queue
slot.

!!! warning "Canonicalise to lowercase .yml"
    Wherever you name topology files — on disk, in CI artifacts, in
    fixture arguments — use exactly `.yml`. Rename `.yaml` files before
    committing them. This is the single most common first-time failure
    with this service.

## Supported providers

Netlab supports multiple providers. `neops-remote-lab` has been exercised
primarily with **Containerlab** via `provider: clab`, which is what every
shipped integration test uses.

```yaml
provider: clab
```

Other Netlab providers (libvirt, virtualbox, external) are not blocked by
`neops-remote-lab` itself — whatever the lab host's `netlab` installation
supports will run — but container-based labs are what this project is built
and validated against. If you stray, expect to maintain your own host
provisioning.

## Vendor defaults: Cisco IOL vs FRRouting

Multi-vendor topologies pick their device kind with the `device:` key, either
globally under `defaults:` or per-node. The two vendors you will see in
neops repos are Cisco IOL and FRRouting. **They are different devices with
different configuration syntax — never conflate them.**

| Kind | Netlab key | Typical image | Use when |
|---|---|---|---|
| Cisco IOL | `device: cisco_iol` | `vrnetlab/cisco_iol` | You need IOS-style CLI for worker-SDK integration tests. |
| FRRouting | `device: frr` | `frrouting/frr` | You need an open-source router with BGP/OSPF for protocol tests. |

Example per-node selection:

```yaml
provider: clab

nodes:
  edge1:
    device: cisco_iol
  core1:
    device: frr

links:
  - edge1-core1
```

!!! info "Pre-built fixtures live in consumer repos"
    The README mentions `simple_iol` and `simple_frr` fixtures. Those are
    conventions defined by downstream consumers (most notably
    `neops-worker-sdk-py` test suites), not fixtures shipped from this
    repository. If your project needs them, see the consuming project's
    test directory for canonical topology files to copy.

## The multipart upload contract

The `POST /lab` endpoint is `multipart/form-data` with three form fields:

| Field | Type | Required | Purpose |
|---|---|---|---|
| `topology` | file | yes | The `.yml` topology. Uploaded filename is preserved in the workdir. |
| `reuse` | string | no (defaults to true) | `"true"` opts into reuse if the content hash matches the running lab. See [lab-lifecycle.md](30-lab-lifecycle.md). |
| `extra_files` | file (repeated) | no | Additional files written alongside the topology before Netlab runs. |

### extra_files: bringing supporting files with the topology

Some topologies reference sibling files — custom device configs, variable
files, template overrides. `extra_files` lets the client ship them alongside
the topology in one request.

<!-- trace: neops_remote_lab/server.py:146 -->
Each uploaded `extra_files` entry is written under the same temp directory
as the topology. The filename is preserved verbatim, and any subpath in the
filename is created via `mkdir(parents=True)` so nested directory layouts
survive the upload round-trip.

Example cURL with one topology and two extras:

```bash
curl -X POST http://$LAB_HOST:8000/lab \
     -H "X-Session-ID: $SESSION" \
     -F "topology=@topologies/spine_leaf.yml" \
     -F "reuse=true" \
     -F "extra_files=@topologies/vars/site.yml" \
     -F "extra_files=@topologies/configs/r1_startup.cfg"
```

Resulting workdir layout (temp path):

```
/tmp/remote_netlab_upload_XXXX/
  spine_leaf.yml
  vars/
    site.yml
  configs/
    r1_startup.cfg
```

!!! tip "Use relative paths in extra_files filenames"
    Upload clients that set `filename=foo/bar.yml` get a nested directory
    on the server. Upload clients that set `filename=bar.yml` get a flat
    file. `RemoteLabClient` uses the topology's filename as-is and does
    not currently wire up `extra_files` automatically; callers that need
    extras must upload them through the REST API directly.

## How Netlab is actually invoked

<!-- trace: neops_remote_lab/netlab/connector.py:96 -->
Once the upload lands and the lab isn't busy, the server calls `run_netlab`
which shells out as `["netlab", "up", "<topology>.yml"]` with the temp
workdir as the working directory. Output is either streamed line-by-line
to the logger (when `NEOPS_NETLAB_STREAM_OUTPUT=1`) or captured and logged
at completion.

<!-- trace: neops_remote_lab/netlab/connector.py:155 -->
After `netlab up` succeeds, the server enumerates nodes with
`netlab inspect -q --instance default --format json
list(nodes.keys())` to discover the device list. The JSON output is parsed
with `ast.literal_eval` and returned as the `devices` payload of the
`POST /lab` response.

Expected device response shape:

```json
{
  "reused": false,
  "devices": [
    {"name": "r1", "raw": {...}},
    {"name": "r2", "raw": {...}}
  ]
}
```

The `raw` field is the full `netlab inspect` output for that node — useful
for retrieving IP addresses, console ports, and container names without a
second round-trip.

## Validating a topology locally

Before uploading, sanity-check the file on the lab host directly:

```bash
netlab test clab
netlab validate path/to/topology.yml
```

A topology that fails `netlab validate` will still be accepted by
`POST /lab` (the server does not preflight-validate), and will then fail
inside Netlab after the session has been promoted. Validating locally
saves a queue slot.

## Where to go next

- [lab-lifecycle.md](30-lab-lifecycle.md) — what the server does with the
  topology after upload: SHA hashing, reuse detection, reference counting.
- [netlab_configuration.md](../deployment/10-netlab-host-setup.md) — installing and
  configuring Netlab on the lab host itself.
