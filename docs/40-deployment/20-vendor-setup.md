---
title: Vendor setup
description: Per-vendor install walkthroughs for FRR, Nokia SR Linux, and Cisco IOL — picked by tab — plus a generic recipe for adding any other Netlab-supported platform.
tags: [how-to, deployment, operator]
crosslink_defines: []
crosslink_references: [netlab, containerlab]
---

# Vendor setup

*For the **decision** — which vendor fits your tests — see [Topology format → Vendor defaults](../10-concepts/40-topology-format.md#vendor-defaults-which-device-to-use). This page is the operator's how-to once the decision is made.*

If you have not installed Netlab + Containerlab yet, start with [Netlab host](10-netlab-host-setup.md) and come back here once `netlab test clab` passes.

!!! tip "Authoritative platform reference is on netlab.tools"
    [netlab.tools/platforms](https://netlab.tools/platforms/) is the source of truth for the Netlab view (per-platform supported modules, image conventions, configuration semantics). [containerlab.dev/manual/kinds](https://containerlab.dev/manual/kinds/) is the source of truth for the container-runtime view.

## Pick the vendor you're setting up

=== "FRR"

    [FRR](https://frrouting.org/) is the open-source default. Containerlab pulls the upstream `frrouting/frr` image; Netlab configures the daemons via `vtysh`-equivalent templates. **No license, no manual image build, no setup beyond `netlab test clab` passing.**

    - **Netlab platform reference:** [netlab.tools/platforms/frr](https://netlab.tools/platforms/frr/)
    - **Upstream:** [frrouting.org](https://frrouting.org/), [GitHub](https://github.com/FRRouting/frr)

    ### Minimal FRR topology

    ```yaml title="examples/topologies/minimal_frr.yml"
    --8<-- "../examples/topologies/minimal_frr.yml"
    ```

    `netlab up` pulls `frrouting/frr` from Docker Hub on first run, then uses the cached image afterward.

    For when FRR is the right call and what its limitations are (no vendor CLI, no hardware-specific behavior, VRF-module dependency), see [Topology format → When FRR is the right call](../10-concepts/40-topology-format.md#when-frr-is-the-right-call).

=== "Nokia SR Linux"

    [Nokia SR Linux](https://www.nokia.com/networks/data-center/service-router-linux-NOS/) is Nokia's container-native NOS — a real network operating system distributed as a public Docker image, free under Nokia's EULA.

    - **Netlab platform reference:** [netlab.tools/platforms/srlinux](https://netlab.tools/platforms/srlinux/)
    - **Containerlab kind reference:** [containerlab.dev/manual/kinds/srl](https://containerlab.dev/manual/kinds/srl/)
    - **Upstream:** [learn.srlinux.dev](https://learn.srlinux.dev/), [GitHub](https://github.com/nokia/srlinux-yang-models)

    ### Pull the image

    Containerlab pulls SR Linux automatically the first time a topology references `kind: srl`, but pre-pulling avoids latency on the first lab:

    ```bash
    docker pull ghcr.io/nokia/srlinux:latest
    ```

    For reproducible CI, **pin a specific release tag** rather than `latest`. The [release tag list](https://github.com/nokia/srlinux-container-image/pkgs/container/srlinux/versions) on GHCR shows what's available; recent releases follow `24.10.1-492` style (year.release.build).

    ### Set SR Linux as the default device

    Add to `~/.netlab.yml`:

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
    --8<-- "../examples/topologies/minimal_srlinux.yml"
    ```

    ### Verify

    ```bash
    netlab show images | grep -i srlinux
    ```

    You should see your `srlinux` device pointing at the image you pinned.

    For when SR Linux is the right call and its trade-offs vs FRR/IOL, see [Topology format → When SR Linux is the right call](../10-concepts/40-topology-format.md#when-sr-linux-is-the-right-call).

=== "Cisco IOL"

    [Cisco IOL (IOS on Linux)](https://netlab.tools/platforms/cisco_iol/) is the IOS image packaged for Containerlab via the [`vrnetlab` fork by hellt](https://github.com/hellt/vrnetlab/). Use it when the function block under test depends on IOS CLI semantics that neither FRR nor SR Linux can replicate.

    - **Netlab platform reference:** [netlab.tools/platforms/cisco_iol](https://netlab.tools/platforms/cisco_iol/)
    - **Containerlab kind reference:** [containerlab.dev/manual/kinds/cisco_iol](https://containerlab.dev/manual/kinds/cisco_iol/)
    - **vrnetlab build path:** [github.com/hellt/vrnetlab/tree/master/cisco/iol](https://github.com/hellt/vrnetlab/tree/master/cisco/iol)

    !!! danger "**Cisco IOL license required** — and the binaries — before this section works"
        Cisco IOL binaries are licensed software. Cisco distributes them only under specific commercial agreements ([Cisco Modeling Labs](https://www.cisco.com/site/us/en/products/networking/modeling-labs/index.html) subscription, EFT/CCO program access, partner agreements). **This guide does not distribute the binaries and cannot help you obtain them.** Acquire them from your Cisco contact, then continue.

        The two binaries you will need:

        - `x86_64_crb_linux-adventerprisek9-ms.iol` — L3 router image
        - `x86_64_crb_linux-adventerprisek9-ms-l2.iol` — L2 switch image

        The exact filenames depend on the Cisco release you receive. Treat the versions in the example commands below (`17.15.01`, `L2-17.15.01`) as placeholders for whatever your binaries report.

    ### Build the IOL container images

    Use the [hellt/vrnetlab fork](https://github.com/hellt/vrnetlab/) — the upstream `vrnetlab` is **not** Containerlab-compatible.

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
        The vrnetlab build expects `.bin`. If your Cisco-supplied file has a different extension, copy or symlink it to `.bin` before running `make docker-image`.

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

    Point Netlab at the images you just built by writing your defaults to `~/.netlab.yml`:

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
        The top-level `device: iol` makes IOL the default device type for topologies that don't specify one. Omit it if you'd rather pick the device per topology.

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

    ```yaml title="topology.yml"
    ---
    provider: clab
    defaults.device: iol
    module: [ ospf ]

    nodes: [ r1, r2 ]
    links: [ r1, r2, r1-r2 ]
    ```

    `netlab up` from that directory boots two IOL routers running OSPF.

=== "Add a new vendor"

    The recipe below is generic and applies to any platform Netlab knows about. For platforms Netlab does **not** know about, you'd need to upstream a new device profile to the [Netlab platform definitions](https://github.com/ipspace/netlab/tree/dev/netsim/devices) — that's an upstream contribution, not something this project's docs cover.

    ### 1. Confirm the platform is supported

    ```bash
    netlab show devices
    ```

    The output lists every device kind your installed Netlab understands. If the platform you want is not listed, upgrade Netlab (`uv tool upgrade networklab` or `pipx upgrade networklab`) and check again. If still missing, the platform isn't supported by Netlab yet.

    ### 2. Acquire the container image

    Three image sources, in descending order of convenience:

    - **Public registry** (FRR, SR Linux) — `docker pull` works directly.
    - **Vendor-gated public registry** (Arista cEOS, Cumulus VX) — manual download from the vendor's site, then `docker load`.
    - **Build from source via vrnetlab** (Cisco IOL, Juniper vMX, …) — clone [hellt/vrnetlab](https://github.com/hellt/vrnetlab/), drop your licensed binary into the platform directory, run `make docker-image`. The Cisco IOL tab above is the canonical example.

    Confirm the image is present:

    ```bash
    docker images --format '{{.Repository}}:{{.Tag}}'
    ```

    ### 3. Tell Netlab which image to use

    Edit `~/.netlab.yml` to map the device kind to your specific image tag:

    ```yaml
    ---
    devices.<device-kind>:
      clab.image: "<registry>/<image>:<tag>"
    ```

    ### 4. Boot a tiny test topology

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

    If both succeed, the new platform is ready to use in `neops-remote-lab` topologies — set `device: <device-kind>` in your test topology and declare a `remote_lab_fixture` against it.

## See also

- **[Topology format → Vendor defaults](../10-concepts/40-topology-format.md#vendor-defaults-which-device-to-use)** — the comparison + decision tree, when each platform is the right call.
- **[Cookbook → Topology recipes](../99-appendix/cookbook.md)** — example topologies for FRR, SR Linux, and the multi-vendor combo.
- **[Netlab host setup](10-netlab-host-setup.md)** — the rootless Netlab + Containerlab install this page assumes.
- **[netlab.tools/platforms](https://netlab.tools/platforms/)** — authoritative per-platform reference for every device Netlab supports.
- **[containerlab.dev/manual/kinds](https://containerlab.dev/manual/kinds/)** — authoritative per-kind reference for the underlying container runtime.
- **[Worker SDK → Remote lab testing](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/)** — once your platform boots, the consumer that drives `remote_lab_fixture` against it.

Next: **[Network enclosure →](25-network-enclosure.md)** to put a security boundary around the host, then **[Run the service →](../30-server/index.md)**.
