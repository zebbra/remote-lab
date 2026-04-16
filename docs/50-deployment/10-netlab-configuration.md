---
page_purpose: how-to
personas_served:
  - devops-engineer
  - senior-network-architect
difficulty_level: intermediate
---

# Netlab Configuration

This page walks through installing Netlab and configuring it for rootless Containerlab on Ubuntu, then layering optional Cisco IOL image support on top. The result is a Remote Lab VM that runs `netlab up` from the server process without sudo prompts and without leaking root-owned files into the workdir — which is the contract `LabManager` expects.

This guide assumes **Ubuntu 24.04+** and is based on the upstream [Netlab installation guide](https://netlab.tools/install/ubuntu/).

## Install Netlab and its toolchain

!!! info "Why?"
    `netlab` orchestrates networks using **KVM/libvirt** for virtual machines, **Docker + Containerlab** for containers, and **Ansible** for configuration. The fastest way to install all required tools is with `netlab install`.

```bash
# Step 1-a: Install system prerequisites
sudo apt-get update && sudo apt-get install -y python3-pip

# Step 1-b: Install Netlab
sudo python3 -m pip install networklab
```

!!! warning "About `--break-system-packages`"
    Use `--break-system-packages` **only on throwaway VMs or CI runners** to suppress Ubuntu 22.04+ pip complaints. For persistent setups, run pip inside a virtual environment instead. Multi-user venv layouts for the Netlab CLI are out of scope for this guide.

```bash
# Step 1-c: Install all backend tooling (Ansible, libvirt, Docker, Containerlab)
netlab install ubuntu ansible libvirt containerlab   # no `sudo` here!
```

!!! warning "Run without sudo"
    Run `netlab install` **without `sudo`** to ensure proper file permissions, group setup, and home-directory configs.

### Validate installation

```bash
netlab test clab
```

This runs a minimal lab with FRR containers and tears it down to validate your install. All systems (Ansible, Docker, libvirt, etc.) must pass.

If you're integrating with the testing framework, continue with the [Testing Setup guide](../40-testing/10-setup.md).

## Configure rootless Containerlab

!!! info "Why?"
    In the default setup `netlab` uses `sudo` to run Containerlab commands, which is not ideal for CI or automation. Since version **0.63**, Containerlab allows rootless operation using a **setuid helper** and group-based access via `clab_admins`. By default Netlab uses an older Containerlab that requires `sudo`, so we need to upgrade it and tell Netlab to use it without sudo.

### Enable password-free Containerlab

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

### Configure Netlab to stop using `sudo`

By default, `netlab` wraps Containerlab calls in `sudo`. Override that by writing rootless provider commands into your user-level Netlab defaults file:

```bash
netlab defaults --user \
  providers.clab.start='containerlab deploy --reconfigure -t clab.yml'

netlab defaults --user \
  providers.clab.stop='containerlab destroy --cleanup -t clab.yml'
```

!!! tip "Where these go"
    These commands write to `~/.netlab.yml` using the correct key structure. **Do not** include `defaults.` in user-level YAML — it will be ignored.

#### Verify the override

```bash
netlab show defaults providers.clab.start
# should output: containerlab deploy --reconfigure -t clab.yml
```

### (Optional) Enable VRF support for FRR labs (Ubuntu)

!!! warning "Required for FRR labs"
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

## Run your first (rootless) lab

Create a simple lab file `topology.yml` in a directory of your choice, e.g., `~/my-lab/`:

```yaml
# topology.yml — minimal two-router OSPF lab
---
provider: clab
defaults.device: frr
module: [ ospf ]

nodes: [ r1, r2 ]
links: [ r1, r2, r1-r2 ]
```

Then run the following commands to start and stop your lab:

```bash
netlab up        # Starts your lab without sudo
# ... run your tests ...
netlab down      # Cleans up lab and files
```

You should see:

```
provider clab: executing containerlab deploy --reconfigure -t clab.yml
```

No `sudo`, no password prompt — ideal for CI.

## Cisco IOL images (optional)

!!! info "What you get"
    Netlab supports [Cisco IOL (IOS on Linux)](https://github.com/hellt/vrnetlab/tree/master/cisco/iol) via Containerlab. These images run fast and light — ideal for routing/switching labs.

!!! warning "Bring your own binaries"
    You need to provide the Cisco IOL binary files yourself, as they are not freely distributable.

### Pre-built images on quay.io

On the [zebbra quay.io registry](https://quay.io/repository/zebbra/neops-labs/cisco_iol) you can find pre-built `cisco_iol` images.

To pull them:

```bash
docker pull quay.io/zebbra/neops-labs/cisco_iol:17.15.01
docker pull quay.io/zebbra/neops-labs/cisco_iol:L2-17.15.01
```

!!! note
    These images are built from the same source as the `vrnetlab` images, but are pre-built and ready to use.

### Build the images yourself

First clone vrnetlab.

!!! warning "Use the containerlab-compatible fork"
    Make sure to use the [hellt fork](https://github.com/hellt/vrnetlab/) compatible with Containerlab and **not** the original repo.

```bash
# 1. Clone the vrnetlab repository
git clone https://github.com/hellt/vrnetlab.git

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

### Verify the images

```bash
docker images --format '{{.Repository}}:{{.Tag}}'
```

Expected output:

```
vrnetlab/cisco_iol:17.15.01
vrnetlab/cisco_iol:L2-17.15.01
```

### Set image defaults in Netlab

The IOL configuration must be **merged into** your existing `~/.netlab.yml` (the file you wrote rootless provider overrides into earlier). Do **not** overwrite the file with a new `cat >` heredoc — that would silently delete your rootless `providers.clab.start` and `providers.clab.stop` overrides.

If `~/.netlab.yml` does not yet exist (you skipped the rootless section), the full file should look like this:

```yaml
# ~/.netlab.yml — combined rootless + IOL device defaults
---
device: iol
providers.clab.start: 'containerlab deploy --reconfigure -t clab.yml'
providers.clab.stop: 'containerlab destroy --cleanup -t clab.yml'
devices.iol:
  clab.image: "vrnetlab/cisco_iol:17.15.01"
devices.ioll2:
  clab.image: "vrnetlab/cisco_iol:L2-17.15.01"
```

If `~/.netlab.yml` already exists with the rootless overrides, **add only the IOL-specific keys** to the existing file:

```yaml
# Add (merge) into existing ~/.netlab.yml — do not overwrite
device: iol
devices.iol:
  clab.image: "vrnetlab/cisco_iol:17.15.01"
devices.ioll2:
  clab.image: "vrnetlab/cisco_iol:L2-17.15.01"
```

Open `~/.netlab.yml` in your editor and paste these keys at the top level alongside the existing `providers.clab.*` keys.

!!! note "About `device: iol`"
    Setting `device: iol` makes it the **default device type** — it is **optional**. You can override this per-topology with `defaults.device: frr` (or any other supported device) inside the topology YAML.

### Verify image config

```bash
netlab show images
```

You should see:

```
iol     → vrnetlab/cisco_iol:17.15.01
ioll2   → vrnetlab/cisco_iol:L2-17.15.01
```

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

## Troubleshooting cheatsheet

| Issue                              | Check with                                                                  |
|------------------------------------|-----------------------------------------------------------------------------|
| Containers fail to start           | `groups $USER` — you must be in `docker` **and** `clab_admins`              |
| Wrong or missing image             | `netlab show images`                                                        |
| `netlab up` asks for sudo password | Ensure `containerlab` runs without sudo, and you're in the right groups     |

You now have a fully rootless, scriptable Netlab setup that works cleanly in CI and without passwords or privilege escalation.
