---
page_purpose: reference
personas_served: [junior-network-engineer, senior-network-architect, devops-engineer]
difficulty_level: intermediate
---

# Topology Format

Netlab accepts more topology syntax than this service supports -- this page draws the line. Use it to plan integrations, scope experiments, and know which knobs are on the table before you start editing YAML.

## The topology envelope

A Remote Lab topology is a **Netlab topology YAML file** — *not* a Containerlab YAML. Netlab is a higher-level abstraction that takes a small declarative file (nodes, links, modules) and generates the lower-level `clab.yml` that Containerlab actually deploys. From Remote Lab's perspective the input is the Netlab YAML; the generated `clab.yml` lives in a temporary working directory created per acquisition (`prepare_workdir()` in `neops_remote_lab/netlab/lab_manager.py:58-75`).

When a client calls `POST /lab` (multipart upload), the server writes the topology and any companion files into a fresh temp directory under `/tmp/remote_netlab_upload_*/` and runs `netlab up <topology>` from that directory. Netlab generates the `clab.yml`, then Containerlab provisions the bridge network and containers. On release, the working directory is discarded.

## File naming: `.yml` is required

The HTTP server accepts both `.yml` and `.yaml` extensions at upload time (`server.py:404-405`). However, the local-mode `LabManager.prepare_workdir()` strictly requires the file to end with `.yml` and raises `ValueError("Topology must be a .yml file")` otherwise (`lab_manager.py:67-71`).

**Practical effect:** if a topology with extension `.yaml` reaches `LabManager` (e.g., a local-mode test calling `LabManager.acquire()` directly, or a server-side execution path that re-uses the file by extension), it fails. Use `.yml` everywhere to avoid this footgun. See [Debugging](../40-testing/40-debugging.md) for the symptom.

## Topology identity via SHA-256 content hash

`LabManager` identifies topologies by the SHA-256 hash of the file content, not by filename or path (`lab_manager.py:46-55`, `:127-129`). Two files with byte-identical content are treated as the same topology and can share a lab when `reuse=True`. Any byte change — including whitespace — produces a different hash and forces a teardown/rebuild on the next acquire.

This has two consequences for callers:

- You can rename a topology file freely without invalidating the running lab.
- A topology cannot be edited "in place" while still re-using the lab: the next acquire sees a new hash and rebuilds.

## Supported providers

Netlab's `provider:` field selects the virtualization backend. The Remote Lab project itself is provider-agnostic — `LabManager` shells out to `netlab up` and lets Netlab dispatch — but in practice:

- **`clab`** (Containerlab) — the default and primary path. The example topology in [Your First Lab Session](../getting-started/20-first-lab.md) uses `provider: clab`. Containerlab provisions a Docker bridge network and per-node containers; this is what the Headscale VPN deployment guide assumes (subnet `192.168.121.0/24`).
- **`libvirt`, `external`, `containers`, others** — Netlab supports these upstream, but they are **not exercised on the standard Remote Lab host setup**. If you depend on them, treat support as best-effort and validate end-to-end on your own host.

For the authoritative list of providers and their semantics, see the upstream [Netlab providers documentation](https://netlab.tools/providers/) (linked from [Resources](../99-appendix/resources.md)).

## Supported Netlab modules

Netlab modules add protocol or feature configuration on top of the base topology — OSPF, BGP, ISIS, MPLS, EVPN, VRFs, and so on. Remote Lab does not filter or wrap modules; whatever the upstream Netlab CLI accepts and whatever the chosen provider/device combination supports is what works.

The [tutorial topology](../getting-started/20-first-lab.md) uses `module: [ ospf ]`, which is the most-validated path on this project. Other modules (BGP, ISIS, VRF, VXLAN, EVPN, MPLS, SR-MPLS, SRv6, the routing module) work as long as the device kind in the topology supports them — but their interaction with the Remote Lab session lifecycle has not been independently verified by this project.

For the authoritative module list and per-device support matrix, defer to the upstream [Netlab modules documentation](https://netlab.tools/module/).

## Supported device kinds

What runs depends on the provider. For `clab` on the Remote Lab host:

| Device kind | Image source | Notes |
|------------|-------------|-------|
| **FRR** (Free Range Routing) | Public, included with Containerlab/Netlab | The reference device used in the tutorial. No license required. |
| **Cisco IOL / IOL-L2** | You build/pull yourself | Cisco does not freely distribute IOL binaries; see the IOL section in [Netlab Configuration](../50-deployment/10-netlab-configuration.md) for image build/pull steps and the [Cisco IOL tutorial](../40-testing/20-local-testing.md#cisco-iol-tutorial) for an end-to-end topology + fixture + test example. |
| **Arista cEOS** | Free download from Arista (registration required) | Import the tarball as a Docker image; reference it via Netlab's `defaults.devices.eos.clab.image`. |
| **Nokia SR Linux** | Public on `ghcr.io/nokia/srlinux` | Free for lab use. |
| **Other Containerlab kinds** (Juniper cRPD, Cumulus VX, etc.) | Vendor-dependent | Check vendor licensing. |

Image availability is a per-host concern: the Remote Lab server can only spin up topologies whose container images are present (or pull-able) on its Docker daemon. See [Resources](../99-appendix/resources.md) for vendor download links.

## `extra_files` upload mechanism

When you call `POST /lab`, you can upload accessory files alongside the topology (custom configs, license tarballs, scripts) using the `extra_files` form field. The server places each file at the relative path you provided as its filename, inside the same temporary working directory as the topology (`server.py:138-154`). The receiving code does:

```python
dest = workdir / item.filename
dest.parent.mkdir(parents=True, exist_ok=True)
```

This means subdirectory paths in the filename are honored. A typical layout:

```
topology.yml
configs/
  r1.cfg
  r2.cfg
```

Sent as:

```bash
curl -F "topology=@topology.yml" \
     -F "extra_files=@configs/r1.cfg;filename=configs/r1.cfg" \
     -F "extra_files=@configs/r2.cfg;filename=configs/r2.cfg" \
     ...
```

…lands at `workdir/configs/r1.cfg` and `workdir/configs/r2.cfg`, which Netlab/Containerlab can reference relatively from the topology.

The Python `RemoteLabClient.acquire()` wraps this for you — see [RemoteLabClient API](../30-client/10-remote-lab-client.md).

## Topology size limits

The hard limit is the **one-lab-per-host constraint**: at any instant the server runs at most one topology. Within that one lab, node count and resource intensity are bounded by the host VM's RAM and CPU, plus per-image memory footprint. There are no software-level node-count caps.

For practical capacity planning (when to add a host, expected concurrency under the FIFO queue, etc.), see [Architecture — One-lab-per-host](10-architecture.md) and the production capacity guidance in [Production](../50-deployment/30-production.md).

## Programmatic device access (no built-in protocol wrappers)

Remote Lab does not wrap NETCONF, YANG, RESTCONF, or gNMI. There is no `ncclient`, `pygnmi`, or model-driven client inside the codebase; the server's job stops once `netlab up` succeeds and the devices are reachable on their Containerlab management subnet. A test that needs to drive a device programmatically uses whatever protocol library it prefers, called against the device IPs returned in `DeviceInfoDto.raw` -- most commonly over SSH via `ansible_host` (Netlab fills that field in the `clab` provider's node inventory, and the dict is passed through verbatim).

The practical consequence: if your test plan assumes a model-driven interface (for example, "configure OSPF via NETCONF and verify via gNMI telemetry"), you bring the client library yourself. `remote_lab_fixture` yields the device list; what you do with those devices -- Scrapli, Netmiko, ncclient, pygnmi, plain `paramiko`, raw sockets -- is outside Remote Lab's concern. This keeps the service small and upgrade-safe at the cost of forcing the protocol choice into your test code.

For the canonical SSH-based patterns used in the existing test suite, see [Pytest Fixtures](../30-client/20-pytest-fixtures.md) and the SSH example on [Using Pytest Fixtures](../getting-started/30-pytest-fixtures.md).

## Netlab features NOT available through Remote Lab

The Remote Lab server constrains a few Netlab patterns that depend on host-level state outside the per-lab sandbox:

- **Per-user `~/.netlab.yml` overrides** — the server's `~/.netlab.yml` is canonical for every uploaded topology. Clients cannot supply per-acquisition Netlab defaults; if you need a different device-default mapping, update the server's `~/.netlab.yml` (see [Netlab Configuration](../50-deployment/10-netlab-configuration.md)).
- **Multi-host labs** — Netlab supports labs spanning multiple physical hosts; Remote Lab does not. Each Remote Lab server runs a single topology on its own host.
- **Persistent state between acquisitions** — every acquire spawns a fresh temp directory and every release deletes it. There is no "scratch" directory for cross-lab artifacts.
- **Nested `include:` of files outside the upload set** — Netlab `include:` directives must resolve to files present in the upload payload (topology + `extra_files`). Anything else fails with a file-not-found at `netlab up` time.
- **Direct `clab.yml` upload** — the server requires a *Netlab* YAML, not a *Containerlab* one. The Containerlab YAML is generated; uploading one directly is not supported.

For per-device-kind setup (images, licenses, provider flags), see [Netlab Configuration](../50-deployment/10-netlab-configuration.md); that page is the canonical home for device-kind-specific details that this topology contract deliberately leaves open.

## See also

- [Lab Lifecycle](30-lab-lifecycle.md) — how acquired labs are reused, torn down, and reference-counted.
- [Session Queue](20-session-queue.md) — how the FIFO queue serializes access when multiple clients race for the lab.
- [REST API — `POST /lab`](../20-server/10-rest-api.md) — the wire format for topology + `extra_files` uploads.
- [Examples](../99-appendix/examples.md) — runnable topology snippets that conform to this contract.
