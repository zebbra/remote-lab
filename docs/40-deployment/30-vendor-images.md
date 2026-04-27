---
title: Vendors & images
description: Pick a router/switch image to run inside Netlab — open-source defaults (FRR, Nokia SR Linux), licensed options (Cisco IOL), and the recipe for adding any other Netlab-supported platform.
tags: [how-to, deployment, operator, topology]
crosslink_defines: []
crosslink_references: [netlab, containerlab]
---

# Vendors & images

A `neops-remote-lab` topology runs whatever device kind Netlab knows how
to drive. This page covers the three platforms you will see most in
neops repositories — **FRR** (the open-source default), **Nokia SR Linux**
(open-source, container-native, no license), and **Cisco IOL** (licensed,
hardware-realistic) — plus a generic recipe for adding any other
Netlab-supported vendor.

If you have not installed Netlab + Containerlab yet, start with
[Netlab host setup](10-netlab-host-setup.md) and come back here once
`netlab test clab` passes.

!!! tip "Authoritative platform reference is on netlab.tools"
    For every device kind on this page, the
    [Netlab platform list](https://netlab.tools/platforms/) is the source
    of truth for the **Netlab** view (per-platform supported modules,
    image conventions, configuration semantics).
    [Containerlab kinds](https://containerlab.dev/manual/kinds/) is the
    source of truth for the **container runtime** view (image registries,
    licensing notes, runtime-specific options). This page picks the
    platforms you'll meet in neops tests and points at both.

---

## Quick comparison

| Platform | Netlab device | License | Boot time | Use when |
|---|---|---|---|---|
| [FRRouting](https://netlab.tools/platforms/frr/) | `frr` | Open-source | seconds | Protocol tests (BGP/OSPF/IS-IS), CI-friendly defaults, no license cost. |
| [Nokia SR Linux](https://netlab.tools/platforms/srlinux/) | `srlinux` | Free for use (Nokia EULA) | ~30 s | YANG/gNMI-driven config, EVPN, segment-routing, Nokia-style CLI semantics, no license fee. |
| [Cisco IOL](https://netlab.tools/platforms/cisco_iol/) | `cisco_iol` | Cisco license required | ~60 s | IOS-style CLI parsing, classic Cisco show-output formats, integration with worker-SDK function blocks targeting IOS. |

If you only need IP routing protocols and cheap CI, use **FRR**. If you
need a real network-OS environment without a license, use **SR Linux**. If
you need IOS CLI semantics, use **Cisco IOL** — and accept the license
overhead.

---

## FRRouting (`device: frr`)

[FRR](https://frrouting.org/) is the open-source default for this
project. Containerlab pulls the upstream `frrouting/frr` image; Netlab
configures the daemons via `vtysh`-equivalent templates.

- **Netlab platform reference:** [netlab.tools/platforms/frr](https://netlab.tools/platforms/frr/) — supported modules, image conventions, default configuration.
- **Containerlab kind reference:** [containerlab.dev/manual/kinds/freebsd](https://containerlab.dev/manual/kinds/freebsd/) (FRR runs under the generic Linux container kind; protocol modules are loaded inside the container).
- **Upstream:** [frrouting.org](https://frrouting.org/), [GitHub](https://github.com/FRRouting/frr).

### When FRR is the right call

- You're testing routing-protocol behavior (OSPFv2/v3, BGP, IS-IS, RIP,
  PIM, BFD, MPLS LDP, VRF, EVPN).
- You want CI to run quickly without licensing concerns.
- The function block under test does not depend on vendor-specific CLI
  output formats.

### Limitations to know about before you commit

FRR is a software router. It does not emulate hardware; it does not
implement vendor-proprietary features; it does not have a Cisco-style or
Junos-style CLI. The places this matters in practice:

- **No vendor CLI semantics.** FRR's `vtysh` resembles IOS at a glance
  but the show-output formats, command grammars, and config artifacts
  differ. Tests that grep for IOS-specific strings (`show ip route`
  field positions, `show running-config` block ordering) will fail
  against FRR. Use Cisco IOL for those.
- **Protocol coverage is broad but not complete.** Cisco-proprietary
  protocols (EIGRP, GLBP, HSRP) have partial or no FRR equivalents.
  Some advanced features within supported protocols (e.g., specific BGP
  RFC drafts) may also be absent. The
  [FRR documentation](https://docs.frrouting.org/) is authoritative
  about what's supported in the version you're running.
- **VRF support requires the Linux VRF kernel module.** Already covered
  in [Netlab host setup → §2.3 VRF support](10-netlab-host-setup.md#optional-23-enable-vrf-support-for-frr-labs-ubuntu).
  Without the module, FRR labs that use VRFs will fail to bring up
  routing instances.
- **Single-process design.** FRR is `frr.service` orchestrating per-protocol
  daemons (`bgpd`, `ospfd`, …). Memory and CPU scale linearly with
  topology size on a single host. For very large topologies (dozens of
  nodes), a single-host Containerlab deployment may saturate before
  protocols converge.
- **No hardware-specific behavior.** Interface flap timers, ASIC-level
  packet handling, queueing, and platform-specific timing are absent.
  Tests that depend on hardware behavior (microbursts, line-rate
  forwarding) cannot run on FRR.
- **Configuration via `vtysh`, not vendor CLI.** Programmatic config
  goes through Netlab's templates, not raw vendor commands. If your
  function block sends raw IOS or Junos CLI, FRR is the wrong target.

For most function-block tests in the worker-SDK ecosystem, FRR is fine —
the integration tests live above CLI-format details. Use FRR by default;
move to a vendor image only when you know you need vendor semantics.

### Minimal FRR topology

```yaml title="examples/topologies/minimal_frr.yml"
--8<-- "examples/topologies/minimal_frr.yml"
```

`netlab up` will pull `frrouting/frr` from Docker Hub on first run, then
use the cached image afterward. No license registration, no manual image
build.

---

## Nokia SR Linux (`device: srlinux`)

[Nokia SR Linux](https://www.nokia.com/networks/data-center/service-router-linux-NOS/)
is Nokia's container-native NOS — a real network operating system
distributed as a public Docker image, **free to use** under Nokia's EULA.
For tests that need a real vendor environment without a commercial
license, SR Linux is the most straightforward path.

- **Netlab platform reference:** [netlab.tools/platforms/srlinux](https://netlab.tools/platforms/srlinux/) — supported modules, image conventions, default configuration template.
- **Containerlab kind reference:** [containerlab.dev/manual/kinds/srl](https://containerlab.dev/manual/kinds/srl/) — image tags, runtime options, license notes.
- **Upstream:** [learn.srlinux.dev](https://learn.srlinux.dev/), [GitHub](https://github.com/nokia/srlinux-yang-models).

### What you get

- **YANG-modeled configuration** with both gNMI and JSON-RPC north-bound
  APIs.
- **Routing protocols:** OSPFv2/v3, IS-IS, BGP (with EVPN), Segment
  Routing (SR-MPLS, SRv6), MPLS LDP, BFD, micro-BFD.
- **Datacenter features:** EVPN/VXLAN with route types 1–5, MAC mobility,
  ESI multi-homing, integrated routing & bridging.
- **Real Nokia CLI** for tests that depend on vendor command grammars.
- **Public image registry** — `ghcr.io/nokia/srlinux:latest` is fetched
  automatically by Containerlab on first lab boot. No registration, no
  build step.

### Pulling the image

Containerlab pulls SR Linux automatically the first time a topology
references `kind: srl`, but you can pre-pull to avoid the latency on the
first lab:

```bash
docker pull ghcr.io/nokia/srlinux:latest
```

For reproducible CI, pin a specific release tag rather than `latest`. The
[release tag list](https://github.com/nokia/srlinux-container-image/pkgs/container/srlinux/versions)
on GHCR shows what's available; recent releases follow the
`24.10.1-492` style format (year.release.build).

### Setting SR Linux as the default device

Add to `~/.netlab.yml` to make SR Linux the default for topologies that
don't specify a `device:`:

```bash
cat > ~/.netlab.yml << 'EOF'
---
device: srlinux
devices.srlinux:
  clab.image: "ghcr.io/nokia/srlinux:24.10.1-492"
EOF
```

Per-topology selection works the same as for any other Netlab device:

```yaml title="examples/topologies/minimal_srlinux.yml"
--8<-- "examples/topologies/minimal_srlinux.yml"
```

### When SR Linux is the right call

- You need a real vendor NOS (not a software router) but cannot or will
  not arrange a commercial license.
- The function block under test uses YANG/gNMI/JSON-RPC config or queries
  — SR Linux has those native.
- You're testing EVPN, segment routing, or other DC-style features.
- You want reproducible CI against a vendor target (image is public, tags
  are stable).

### Limitations to know about

- **Container-only.** SR Linux ships as a Docker image; it does not run
  on real Nokia hardware via this path. Behavior matches the production
  NOS for control-plane and config; data-plane is a software fast path
  with realistic-but-not-identical timing characteristics.
- **License terms are Nokia's, not open-source.** The image is free to
  use under Nokia's EULA but is not distributed under an OSI-approved
  open-source license. If your project's licensing audit requires
  OSI-approved deps, FRR is the safer pick.
- **Resource footprint is heavier than FRR.** Each SR Linux container
  takes ~1 GB RAM and a few cores during boot. Plan host capacity
  accordingly for larger topologies.
- **Boot time is ~30 s per node.** Significantly faster than IOL or
  vMX, slower than FRR (which is seconds). For large topologies use
  Netlab's parallelism and the Remote Lab's `reuse_lab=True` to amortize.

### Verify Netlab sees the image

```bash
netlab show images | grep -i srlinux
```

You should see your `srlinux` device pointing at the image you pinned.

---

## Cisco IOL (`device: cisco_iol`, license required)

[Cisco IOL (IOS on Linux)](https://netlab.tools/platforms/cisco_iol/) is
the IOS image packaged for Containerlab via the
[`vrnetlab` fork by hellt](https://github.com/hellt/vrnetlab/). Use it
when the function block under test depends on IOS CLI semantics that
neither FRR nor SR Linux can replicate.

- **Netlab platform reference:** [netlab.tools/platforms/cisco_iol](https://netlab.tools/platforms/cisco_iol/) — supported modules, image conventions.
- **Containerlab kind reference:** [containerlab.dev/manual/kinds/cisco_iol](https://containerlab.dev/manual/kinds/cisco_iol/) — runtime options, image tagging conventions, licensing notes.
- **vrnetlab build path:** [github.com/hellt/vrnetlab/tree/master/cisco/iol](https://github.com/hellt/vrnetlab/tree/master/cisco/iol).

!!! danger "You need a Cisco IOL license — and the binaries — before this section works"
    Cisco IOL binaries are licensed software. Cisco distributes them only
    under specific commercial agreements
    ([Cisco Modeling Labs](https://www.cisco.com/site/us/en/products/networking/modeling-labs/index.html)
    subscription, EFT/CCO program access, partner agreements). **This
    guide does not distribute the binaries and cannot help you obtain
    them.** Acquire them from your Cisco contact, then continue.

    The two binaries you will need:

    - `x86_64_crb_linux-adventerprisek9-ms.iol` — L3 router image
    - `x86_64_crb_linux-adventerprisek9-ms-l2.iol` — L2 switch image

    The exact filenames depend on the Cisco release you receive. Treat
    the versions in the example commands below (`17.15.01`,
    `L2-17.15.01`) as placeholders for whatever your binaries report.

If you do not have IOL access, **stick with FRR or SR Linux** — both are
free and both cover most function-block test scenarios.

### Build the IOL container images

Use the [hellt/vrnetlab fork](https://github.com/hellt/vrnetlab/) — the
upstream `vrnetlab` is **not** Containerlab-compatible.

```bash
# 1. Clone the vrnetlab fork
git clone https://github.com/hellt/vrnetlab.git

# 2. Place your Cisco IOL binaries into the build directory
#    (replace the source paths with the location of your licensed binaries;
#    keep the .bin extension — the build expects it)
cp /path/to/your/x86_64_crb_linux-adventerprisek9-ms.iol \
   vrnetlab/cisco/iol/cisco_iol-17.15.01.bin

cp /path/to/your/x86_64_crb_linux-adventerprisek9-ms-l2.iol \
   vrnetlab/cisco/iol/cisco_iol-L2-17.15.01.bin

# 3. Build the Docker images
cd vrnetlab/cisco/iol
make docker-image
```

!!! note "The `.bin` extension is required"
    The vrnetlab build expects `.bin`. If your Cisco-supplied file has a
    different extension, copy or symlink it to `.bin` before running
    `make docker-image`.

### Verify the images are present

```bash
docker images --format '{{.Repository}}:{{.Tag}}' | grep cisco_iol
```

Expected output (versions reflect what you built):

```text
vrnetlab/cisco_iol:17.15.01
vrnetlab/cisco_iol:L2-17.15.01
```

### Tell Netlab which IOL image to use

Point Netlab at the images you just built by writing your defaults to
`~/.netlab.yml`:

```bash
cat > ~/.netlab.yml << 'EOF'
---
device: iol
devices.iol:
  clab.image: "vrnetlab/cisco_iol:17.15.01"
devices.ioll2:
  clab.image: "vrnetlab/cisco_iol:L2-17.15.01"
EOF
```

!!! note "Setting `device: iol` is optional"
    The top-level `device: iol` makes IOL the default device type for
    topologies that don't specify one. Omit it if you'd rather pick the
    device per topology.

### Verify Netlab sees the images

```bash
netlab show images
```

You should see:

```text
iol     → vrnetlab/cisco_iol:17.15.01
ioll2   → vrnetlab/cisco_iol:L2-17.15.01
```

### Test your IOL lab

Create a simple IOL lab file `topology.yml` (replace `iol-lab/` with any
directory):

```yaml
---
provider: clab
defaults.device: iol
module: [ ospf ]

nodes: [ r1, r2 ]
links: [ r1, r2, r1-r2 ]
```

`netlab up` from that directory boots two IOL routers running OSPF.

---

## Other Netlab-supported platforms

Netlab supports many more platforms than the three above. The full list
is on [netlab.tools/platforms](https://netlab.tools/platforms/). The ones
you are most likely to encounter in neops repos:

| Platform | Netlab device | License | Image source |
|---|---|---|---|
| [Arista cEOS](https://netlab.tools/platforms/eos/) | `eos` | Free for use (Arista TAC registration) | [arista.com/EOS-CEOS](https://www.arista.com/en/support/software-download) — manual download |
| [Cumulus Linux (NVIDIA)](https://netlab.tools/platforms/cumulus/) | `cumulus` | Free community version | [hub.docker.com/r/cumulusnetworks/cumulus-vx](https://hub.docker.com/r/cumulusnetworks/cumulus-vx/) |
| [Mikrotik RouterOS](https://netlab.tools/platforms/routeros/) | `routeros` | Free virtual edition (CHR) | [mikrotik.com/download](https://mikrotik.com/download) |
| [Cisco IOS XE / CSR1000v](https://netlab.tools/platforms/csr/) | `csr` | License required | Cisco partner channel |
| [Cisco NX-OS](https://netlab.tools/platforms/nxos/) | `nxos` | License required | Cisco partner channel |
| [Juniper vSRX / vMX](https://netlab.tools/platforms/vsrx/) | `vsrx`, `vmx` | License required | Juniper partner channel |
| [BIRD](https://netlab.tools/platforms/bird/) | `bird` | Open-source | [bird.network.cz](https://bird.network.cz/) |

Before adding any of these, check the platform page on netlab.tools for
the per-platform module-support matrix — not every protocol module works
on every platform.

---

## Adding a new vendor / image

The recipe below is generic and applies to any platform Netlab knows about.
For platforms Netlab does **not** know about, you would need to upstream a
new device profile to the
[Netlab platform definitions](https://github.com/ipspace/netlab/tree/dev/netsim/devices)
— that's an upstream contribution, not something this project's docs
cover.

### 1. Confirm the platform is supported by your Netlab version

```bash
netlab show devices
```

The output lists every device kind your installed Netlab understands. If
the platform you want is not listed, upgrade Netlab (`pipx upgrade
networklab`) and check again. If still missing, the platform isn't
supported by Netlab yet.

### 2. Acquire the container image

There are three image sources, in descending order of convenience:

- **Public registry** (FRR, SR Linux) — `docker pull` works directly. No
  registration, no build.
- **Vendor-gated public registry** (Arista cEOS, Cumulus VX) — manual
  download from the vendor's site, then `docker load` to install
  locally.
- **Build from source via vrnetlab** (Cisco IOL, Juniper vMX, …) — clone
  [hellt/vrnetlab](https://github.com/hellt/vrnetlab/), drop your
  licensed binary into the platform directory, run `make docker-image`.
  Cisco IOL above is the canonical example.

Confirm the image is present:

```bash
docker images --format '{{.Repository}}:{{.Tag}}'
```

### 3. Tell Netlab which image to use

Edit `~/.netlab.yml` to map the device kind to your specific image tag.
The structure is `devices.<device-kind>.clab.image`:

```yaml
---
devices.<device-kind>:
  clab.image: "<registry>/<image>:<tag>"
```

Optionally set the top-level `device: <device-kind>` to make it the
default for topologies that don't specify one.

### 4. Verify

```bash
netlab show images
```

Confirm your device kind shows the right image tag.

### 5. Boot a tiny test topology

```yaml
provider: clab
defaults.device: <device-kind>
nodes: [ r1, r2 ]
links: [ r1-r2 ]
```

```bash
netlab up
netlab down --cleanup
```

If both succeed, the new platform is ready to use in `neops-remote-lab`
topologies — set `device: <device-kind>` in your test topology and
declare a `remote_lab_fixture` against it.

### 6. (Optional) Make it the default in your own deployment

If most of your tests target this new platform, point `~/.netlab.yml`'s
top-level `device:` at it, and the topology files can omit the
`defaults.device` line entirely.

---

## Where to go next

- **[Topology format](../10-concepts/40-topology-format.md)** — the
  YAML shape Netlab expects, the `extra_files` upload contract, and the
  `.yml` extension constraint.
- **[Netlab host setup](10-netlab-host-setup.md)** — the rootless
  Netlab + Containerlab install this page assumes you've already done.
- **[netlab.tools/platforms](https://netlab.tools/platforms/)** —
  authoritative per-platform reference for every device Netlab supports.
- **[containerlab.dev/manual/kinds](https://containerlab.dev/manual/kinds/)**
  — authoritative per-kind reference for the underlying container
  runtime.
- **[neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py)**
  — once your platform boots, the function-block test harness in
  worker-sdk is the consumer that drives `remote_lab_fixture` against
  it.
