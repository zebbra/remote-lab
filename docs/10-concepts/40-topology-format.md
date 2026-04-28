---
title: Topology format
description: The Netlab YAML shape neops-remote-lab expects — provider choice, node/link structure, vendor defaults, and the extra_files multipart upload contract.
tags: [concept, testing, deployment]
crosslink_defines: [topology]
crosslink_references: []
---

# Topology format

*The Netlab YAML shape `neops-remote-lab` consumes — provider choice, node/link structure, vendor defaults, and the `extra_files` upload contract.*

A **topology** is a single YAML file (`.yml` or `.yaml` — both are
accepted, case-insensitive) that tells Netlab what network to build:
which nodes, which links, which provider. `neops-remote-lab` accepts that
file over HTTP, copies it into a clean workdir, and hands it to the Netlab
CLI verbatim. The YAML dialect is **Netlab's**, not ours.

> **Why a page on topology format if Netlab owns the schema?** The
> `extra_files` upload contract is enforced in *this* server, not in
> Netlab, and fixture consumers often inherit topologies from upstream
> repos and want a single-page reference for the surface they're using.

## The minimal topology

A working Netlab topology needs a provider, at least one node, and usually
some links. Here is the smallest useful starting point — two FRR routers on
one link:

```yaml title="minimal_frr.yml"
--8<-- "../examples/topologies/minimal_frr.yml"
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

## Supported providers

Netlab supports
[multiple providers](https://netlab.tools/labs/) — Containerlab,
libvirt/KVM, VirtualBox, external. `neops-remote-lab` has been exercised
primarily with **[Containerlab](https://containerlab.dev/)** via
`provider: clab`, which is what every shipped integration test uses.

```yaml
provider: clab
```

Other Netlab providers (libvirt, virtualbox, external) are not blocked by
`neops-remote-lab` itself — whatever the lab host's `netlab` installation
supports will run — but container-based labs are what this project is built
and validated against. If you stray, expect to maintain your own host
provisioning.

## Vendor defaults: which device to use {#vendor-defaults-which-device-to-use}

Multi-vendor topologies pick their device kind with the `device:` key, either globally under `defaults:` or per-node. **Different devices have different configuration semantics — never conflate them.** The three you'll meet in 95% of neops topologies:

<div class="grid cards" markdown>

-   :material-flash:{ .lg .middle } &nbsp; **FRR**

    ---

    `device: frr` &middot; open-source &middot; seconds boot

    - Protocol tests (BGP, OSPF, IS-IS, RIP, BFD, MPLS LDP, EVPN)
    - CI defaults — no license, fastest boot
    - No vendor CLI semantics (don't grep for IOS strings)

    [Setup →](../40-deployment/40-vendor-setup.md) &middot; [netlab.tools/frr](https://netlab.tools/platforms/frr/)

-   :material-shield-network:{ .lg .middle } &nbsp; **Nokia SR Linux**

    ---

    `device: srlinux` &middot; free EULA &middot; ~30 s boot

    - YANG / gNMI / JSON-RPC native
    - EVPN, segment routing, DC fabrics
    - Container-only, ~1 GB RAM per node

    [Setup →](../40-deployment/40-vendor-setup.md) &middot; [netlab.tools/srlinux](https://netlab.tools/platforms/srlinux/)

-   :material-router-network:{ .lg .middle } &nbsp; **Cisco IOL**

    ---

    `device: cisco_iol` &middot; license required &middot; ~60 s boot

    - IOS CLI semantics
    - [Worker SDK function blocks](https://docs.neops.io/neops-worker-sdk-py/docs/function-blocks/) targeting Cisco
    - vrnetlab build path; license overhead

    [Setup →](../40-deployment/40-vendor-setup.md) &middot; [netlab.tools/cisco_iol](https://netlab.tools/platforms/cisco_iol/)

</div>

If you only need IP **routing protocols** and cheap CI, use **FRR**. If you need a **real network-OS environment** without a license, use **SR Linux**. If you need **IOS CLI semantics**, use **Cisco IOL** — and *accept the license overhead*.

### When FRR is the right call

FRR is a software router. *It does not emulate hardware; it does not implement vendor-proprietary features; it does not have a Cisco-style or Junos-style CLI.* Pick FRR when:

- You're testing routing-protocol behaviour (OSPFv2/v3, BGP, IS-IS, RIP, PIM, BFD, MPLS LDP, VRF, EVPN).
- You want CI to run quickly without licensing concerns.
- The function block under test does not depend on vendor-specific CLI output formats.

??? info "FRR limitations to know about before you commit"

    - **No vendor CLI semantics.** `vtysh` resembles IOS at a glance but show-output formats, command grammars, and config artifacts differ. Tests that grep for IOS-specific strings will fail against FRR.
    - **Protocol coverage is broad but not complete.** Cisco-proprietary protocols (EIGRP, GLBP, HSRP) have partial or no FRR equivalents. The [FRR documentation](https://docs.frrouting.org/) is authoritative about what's supported.
    - **VRF support requires the Linux VRF kernel module.** Covered in [Netlab host setup → VRF support](../40-deployment/10-netlab-host-setup.md#optional-23-enable-vrf-support-for-frr-labs-ubuntu).
    - **No hardware-specific behavior.** Interface flap timers, ASIC-level packet handling, queueing, and platform-specific timing are absent.
    - **Configuration via `vtysh`, not vendor CLI.** Programmatic config goes through Netlab's templates, not raw vendor commands.

    For most function-block tests, FRR is fine — the integration tests live above CLI-format details. Use FRR by default; move to a vendor image only when you know you need vendor semantics.

### When SR Linux is the right call

A real vendor NOS, no license fee:

- Function block uses YANG / gNMI / JSON-RPC config or queries.
- You're testing EVPN, segment routing, or other DC-style features.
- You want reproducible CI against a vendor target (public image, stable tags).

??? info "SR Linux trade-offs"

    Container-only (no real hardware via this path); not OSI-approved open-source (Nokia EULA); ~1 GB RAM per node; ~30 s boot. For large topologies, prefer Netlab's parallelism and `reuse_lab=True` to amortize boot cost — see [Session queue → Shared topologies collapse the queue](20-session-queue.md#shared-topologies-collapse-the-queue).

### When Cisco IOL is the right call

When the function block depends on IOS CLI semantics neither FRR nor SR Linux can replicate (show-output parsing, IOS configuration block ordering, classic show commands), and you can arrange a Cisco license. **Without IOL access, stick with FRR or SR Linux** — both are free and both cover most function-block test scenarios.

### Other Netlab-supported platforms

Netlab supports many more platforms — the full list is on [netlab.tools/platforms](https://netlab.tools/platforms/). The ones you are most likely to encounter:

| Platform | Netlab device | License |
|---|---|---|
| [Arista cEOS](https://netlab.tools/platforms/eos/) | `eos` | Free (Arista TAC registration) |
| [Cumulus Linux (NVIDIA)](https://netlab.tools/platforms/cumulus/) | `cumulus` | Free community version |
| [Mikrotik RouterOS](https://netlab.tools/platforms/routeros/) | `routeros` | Free virtual edition (CHR) |
| [Cisco IOS XE / CSR1000v](https://netlab.tools/platforms/csr/) | `csr` | License required |
| [Cisco NX-OS](https://netlab.tools/platforms/nxos/) | `nxos` | License required |
| [Juniper vSRX / vMX](https://netlab.tools/platforms/vsrx/) | `vsrx`, `vmx` | License required |
| [BIRD](https://netlab.tools/platforms/bird/) | `bird` | Open-source |

Before adding any of these, check the platform page on netlab.tools for the module-support matrix — not every protocol module works on every platform.

For per-vendor install walkthroughs (image pull, license setup, vrnetlab build), see [Vendor setup](../40-deployment/40-vendor-setup.md).

### Example: per-node selection

```yaml
provider: clab

nodes:
  spine1:
    device: srlinux
  leaf1:
    device: frr

links:
  - leaf1-spine1
```

!!! info "Pre-built fixtures live in consumer repos"
    The README mentions `simple_iol` and `simple_frr` fixtures. Those are
    conventions defined by downstream consumers — most notably the
    [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/)
    test suites
    ([Remote lab integration guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/)) —
    not fixtures shipped from this repository. If your project needs
    them, see the consuming project's test directory for canonical
    topology files to copy.

## The multipart upload contract

The `POST /lab` endpoint is `multipart/form-data` with three form fields:

| Field | Type | Required | Purpose |
|---|---|---|---|
| `topology` | file | yes | The Netlab topology — `.yml` or `.yaml`, case-insensitive. The uploaded filename is preserved in the workdir. |
| `reuse` | string | no (defaults to true) | `"true"` opts into reuse if the content hash matches the running lab. See [Lab lifecycle](30-lab-lifecycle.md). |
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

- [Lab Lifecycle](30-lab-lifecycle.md) — what the server does with the topology after upload: SHA hashing, reuse detection, reference counting.
- [Vendor setup](../40-deployment/40-vendor-setup.md) — per-vendor install walkthroughs (FRR auto-pull, SR Linux pin, Cisco IOL build).
- [Netlab host setup](../40-deployment/10-netlab-host-setup.md) — installing and configuring Netlab on the lab host itself.
