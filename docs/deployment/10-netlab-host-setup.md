---
title: Netlab host setup
description: Install and configure rootless Netlab plus Containerlab on Ubuntu for running lab topologies under neops-remote-lab.
tags: [how-to, deployment, operator]
crosslink_defines: [netlab, containerlab]
crosslink_references: [remote-lab]
---

# Rootless Netlab + Containerlab on Ubuntu

*A concise, CI-ready installation and configuration guide*

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
netlab [installation guide](https://netlab.tools/install/ubuntu/).

The PyPI package is `networklab`; the installed CLI is `netlab`.

```bash
# Step 1-a: Install system prerequisites and pipx
sudo apt-get update
sudo apt-get install -y pipx

# Step 1-b: Install netlab via pipx
pipx install networklab
pipx ensurepath
```

!!! warning "Ubuntu 24.04+"
    Ubuntu 24.04 marks the system Python as [PEP 668](https://peps.python.org/pep-0668/)
    *externally managed*; plain `pip install` into the system interpreter fails with
    `error: externally-managed-environment`. `pipx` sidesteps this by installing
    `networklab` into its own isolated venv under `~/.local/pipx/venvs/networklab`
    and exposing the `netlab` CLI on `PATH` via `pipx ensurepath`.

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

If you're authoring tests against Remote Lab, see [Pytest fixtures](../client/10-pytest-fixtures.md) for the public fixture API, or [Quickstart](../getting-started/10-quickstart.md) to run your first lab-backed test.

For consumers integrating via `neops-worker-sdk-py`, that repo owns the `remote_lab_fixture` consumer surface.

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

## 4. – Cisco IOL images (optional)

`netlab` supports [Cisco IOL (IOS on Linux)](https://github.com/hellt/vrnetlab/tree/master/cisco/iol) via
Containerlab. These images run fast and light — ideal for routing/switching labs.

!!! warning "License restriction"
    You need to provide the Cisco IOL binary files yourself, as they are not freely distributable.

### Images in zebbra quay.io

On the [zebbra quay.io registry](https://quay.io/repository/zebbra/neops-labs/cisco_iol) you can find the cisco_iol images.

To clone them to your local machine, run:

```bash
docker pull quay.io/zebbra/neops-labs/cisco_iol:17.15.01
docker pull quay.io/zebbra/neops-labs/cisco_iol:L2-17.15.01
```

!!! note
    These images are built from the same source as the `vrnetlab` images, but are pre-built and ready to use.

### Build the images

First clone vrnetlab.

!!! note
    Make sure to use the [fork](https://github.com/hellt/vrnetlab/) compatible with containerlabs and not the original repo.

```bash
# 1. Clone the vrnetlab repository
git clone ssh://github.com/hellt/vrnetlab.git

# 2. Place Cisco IOL binary in build directory
cp x86_64_crb_linux-adventerprisek9-ms.iol \
   vrnetlab/cisco/iol/cisco_iol-17.15.01.bin

cp x86_64_crb_linux-adventerprisek9-ms-l2.iol \
   vrnetlab/cisco/iol/cisco_iol-L2-17.15.01.bin
```

!!! note
    The `.bin` extension is required.

```bash
# 3. Build the Docker images
cd vrnetlab/cisco/iol
make docker-image
```

### Check the images

```bash
docker images --format '{{.Repository}}:{{.Tag}}'
```

Expected output:

```text
vrnetlab/cisco_iol:17.15.01
vrnetlab/cisco_iol:L2-17.15.01
```

---

### Set image defaults in Netlab

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

!!! note
    Setting `device: iol` makes it the **default device type** — **optional**.
    You can override this per-topology.

### Verify image config

```bash
netlab show images
```

You should see:

```text
iol     → vrnetlab/cisco_iol:17.15.01
ioll2   → vrnetlab/cisco_iol:L2-17.15.01
```

---

### Test your IOL lab

Create a simple IOL lab file `topology.yml` in a directory of your choice, e.g., `~/iol-lab/`:

```yaml
---
provider: clab
defaults.device: iol
module: [ ospf ]

nodes: [ r1, r2 ]
links: [ r1, r2, r1-r2 ]
```

## Troubleshooting Cheatsheet

| Issue                              | Check with                                                                  |
|------------------------------------|-----------------------------------------------------------------------------|
| Containers fail to start           | `groups $USER` – you must be in `docker` **and** `clab_admins`              |
| Wrong or missing image             | `netlab show images`                                                        |
| `netlab up` asks for sudo password | Ensure `containerlab` runs without sudo, and you're in the right groups     |
| `pip install` errors with `externally-managed-environment` | PEP 668 is blocking system pip on Ubuntu 24.04+; install via `pipx install networklab` instead (see §1 pipx warning) |
| Forward link to `testing-framework.md` is broken | The old page was split into [Pytest fixtures](../client/10-pytest-fixtures.md) and [Quickstart](../getting-started/10-quickstart.md); update references to point at those |

You now have a **fully rootless, scriptable Netlab setup** that works cleanly in CI and without passwords or privilege
escalation.
