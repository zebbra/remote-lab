---
title: Netlab host setup
description: Install and configure rootless Netlab plus Containerlab on Ubuntu for running lab topologies under neops-remote-lab.
tags: [how-to, deployment, operator]
crosslink_defines: [netlab, containerlab]
crosslink_references: [remote-lab]
---

# Rootless Netlab + Containerlab on Ubuntu

*A concise, CI-ready installation and configuration guide.*

The Remote Lab Manager refuses to start without `netlab` on `PATH`. This
page is the **prerequisite for everything else in deployment**: install
[Netlab](https://netlab.tools/) and [Containerlab](https://containerlab.dev/)
rootless on Ubuntu, validate the install with `netlab test clab`, then
move on to [Vendors & images](30-vendor-images.md) (which device kinds
to ship) and [Headscale VPN](20-headscale-vpn.md) (how clients reach
the lab).

---

## 1. – Install *netlab* and its toolchain (no `sudo`)

!!! info "Why?"
    `netlab` orchestrates networks using:

    - **KVM/libvirt** for virtual machines
    - **Docker + Containerlab** for containers
    - **Ansible** for configuration

    The fastest way to install all required tools is with `netlab install`.

### Installation Steps

This guide assumes you are using **Ubuntu 24.04+** and is based on the
upstream [netlab installation guide](https://netlab.tools/install/ubuntu/).
The PyPI package is `networklab`; the installed CLI is `netlab`.

Install it as an isolated tool — the same shape used for the
`neops-remote-lab` server CLI, so both binaries cohabit cleanly.

=== "uv (recommended)"

    ```bash
    # Install uv first if you don't have it
    curl -LsSf https://astral.sh/uv/install.sh | sh

    # Install the netlab CLI as an isolated tool
    uv tool install networklab
    ```

    [`uv tool install`](https://docs.astral.sh/uv/concepts/tools/) drops
    the CLI in `~/.local/bin` (or `uv tool dir`) inside an isolated
    environment that uv manages. No system-Python contamination.

=== "pipx"

    ```bash
    sudo apt-get update
    sudo apt-get install -y pipx
    pipx install networklab
    pipx ensurepath
    ```

    Installs into `~/.local/pipx/venvs/networklab` and exposes the
    `netlab` CLI on `PATH`. Re-login (or source your shell's RC file)
    after the first `pipx ensurepath`.

=== "pip (not recommended on Ubuntu 24.04+)"

    ```bash
    python -m venv ~/.venvs/networklab
    ~/.venvs/networklab/bin/pip install networklab
    ln -s ~/.venvs/networklab/bin/netlab ~/.local/bin/
    ```

    Manual virtualenv plus a symlink. On Ubuntu 24.04+ a plain
    `pip install networklab` fails with `error: externally-managed-environment`
    ([PEP 668](https://peps.python.org/pep-0668/)) — that's why uv or
    pipx is preferred.

```bash
# Step 1-c: Install all backend tooling (Ansible, libvirt, Docker, Containerlab)
netlab install ubuntu ansible libvirt containerlab # no `sudo` here!
```

!!! warning
    Run this **without `sudo`** to ensure proper file permissions, group setup, and home-directory configs.

---

### Validate installation

```bash
netlab test clab
```

This runs a minimal lab with FRR containers and tears it down to validate your install.
All systems (Ansible, Docker, libvirt, etc.) must pass.

---

If you're authoring tests against Remote Lab, see [Pytest fixtures](../20-client/10-pytest-fixtures.md) for the public fixture API, or [Quickstart](../getting-started/10-quickstart.md) to run your first lab-backed test.

For consumers integrating via the [Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/),
that project owns the `remote_lab_fixture` consumer surface — see its
[Remote lab testing guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/).

## 2. – Configure Rootless Containerlab

!!! info "Why?"
    In the default setup netlab uses `sudo` to run Containerlab commands, which is not ideal for CI or automation.

    Since version **0.63**, Containerlab allows rootless operation using a **setuid helper** and group-based access via
    `clab_admins`. By default **netlab** uses an older version of Containerlab that requires `sudo` to run, so we need to
    upgrade it and configure netlab to use it without sudo.

### 2.1. Enable password-free Containerlab

```bash
# Upgrade to a recent Containerlab version (>= 0.63)
sudo containerlab version upgrade

# Ensure the binary is setuid-root
sudo chmod u+s $(command -v containerlab)

# Add yourself to required groups
sudo groupadd -r clab_admins         # safe to repeat
sudo usermod -aG docker,clab_admins $USER

# Apply new group memberships in current session
newgrp clab_admins
```

#### Check that it works

```bash
containerlab version
```

You should **see the version banner without any password prompt**.

### 2.2. Configure netlab to stop using `sudo`

By default, `netlab` wraps Containerlab calls in `sudo`. We override that:

```bash
netlab defaults --user \
  providers.clab.start='containerlab deploy --reconfigure -t clab.yml'

netlab defaults --user \
  providers.clab.stop='containerlab destroy --cleanup -t clab.yml'
```

!!! note
    These commands write to `~/.netlab.yml` using the correct key structure.
    **Do not** include `defaults.` in user-level YAML — it will be ignored.

#### Verify override

```bash
netlab show defaults providers.clab.start
# should output: containerlab deploy --reconfigure -t clab.yml
```

### (Optional) 2.3. Enable VRF support for FRR labs (Ubuntu)

!!! important "Important for FRR labs"
    To run FRR labs rootless, Ubuntu requires the VRF kernel module to be installed and loaded.

```bash
# Install VRF kernel module
sudo apt update
sudo apt install linux-modules-extra-$(uname -r) || sudo apt install linux-generic

# Load the VRF module
sudo modprobe vrf

# Verify VRF module is loaded
lsmod | grep vrf
```

---

## 3. – Run your first (rootless) lab

Create a simple lab file `topology.yml` in a directory of your choice, e.g., `~/my-lab/`.

```yaml
# Create a minimal topology file (topology.yml):
---
provider: clab
defaults.device: frr
module: [ ospf ]

nodes: [ r1, r2 ]
links: [ r1, r2, r1-r2 ]
```

Then run the following commands to start and stop your lab:

```bash
# Run from your topology.yml directory
netlab up        # Starts your lab without sudo
# ... run your tests ...
netlab down      # Cleans up lab and files
```

```text
You should see:

provider clab: executing containerlab deploy --reconfigure -t clab.yml
```

No `sudo`, no password prompt — ideal for CI.

---

## 4. – Pick a router/switch image to run

Once `netlab test clab` passes, you have a working lab host that can boot
the open-source [FRR](https://netlab.tools/platforms/frr/) image out of
the box. For everything else — open-source vendor stacks like
[Nokia SR Linux](https://netlab.tools/platforms/srlinux/), licensed
images like [Cisco IOL](https://netlab.tools/platforms/cisco_iol/), or
adding any other Netlab-supported platform — see the dedicated
[Vendors & images](30-vendor-images.md) guide.

The vendor page covers when each platform is the right call, the FRR
limitations to know about before you commit, the SR Linux setup (free,
public registry, no license), the Cisco IOL build path (license
required), and a generic recipe for adding any other Netlab platform.

---

## Troubleshooting Cheatsheet

| Issue                              | Check with                                                                  |
|------------------------------------|-----------------------------------------------------------------------------|
| Containers fail to start           | `groups $USER` – you must be in `docker` **and** `clab_admins`              |
| Wrong or missing image             | `netlab show images`                                                        |
| `netlab up` asks for sudo password | Ensure `containerlab` runs without sudo, and you're in the right groups     |
| `pip install` errors with `externally-managed-environment` | PEP 668 is blocking system pip on Ubuntu 24.04+; install via `pipx install networklab` instead (see §1 pipx warning) |

You now have a **fully rootless, scriptable Netlab setup** that works cleanly in CI and without passwords or privilege
escalation.
