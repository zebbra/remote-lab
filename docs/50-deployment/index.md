---
page_purpose: overview
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: intermediate
---

# Deployment

Deploying a Remote Lab instance means preparing a VM with Netlab, networking it into your tailnet, and running the server as a long-lived process. The three pages below follow that sequence -- each stage assumes the previous stage is complete.

## Deployment roadmap

**Stage 1 -- Prepare the lab host.** [Netlab Configuration](10-netlab-configuration.md) walks through installing Netlab and Containerlab on a fresh Ubuntu VM, pulling the container images your tests will use, and verifying `netlab up` works against a scratch topology. This stage is a one-time setup: once `netlab test clab` passes, the host is ready to run labs and you do not touch this layer again until you add a new device kind.

**Stage 2 -- Put the host on the network.** [Headscale VPN](20-headscale-vpn.md) covers running Headscale + Headplane in Docker, approving the lab host as a subnet router so CI runners and developer laptops can reach lab container management IPs, and configuring ACLs. Skip this stage if your deployment model is a flat internal network -- the server will serve plain HTTP either way. Come back here when you need secure cross-site access.

**Stage 3 -- Run the service.** [Production Deployment](30-production.md) is where the FastAPI server actually starts: systemd unit, reverse proxy + TLS recipe, monitoring stack (Prometheus/Grafana/Loki), secret management, backup and restore procedures, and capacity-planning numbers. This is the page you return to whenever the service's operational posture changes.

## Prerequisites

Before working through the deployment pages, you should have:

- An Ubuntu 24.04+ host with Docker installed
- Familiarity with the [Architecture](../10-concepts/10-architecture.md) and the one-lab-per-host constraint
- The server [Configuration](../20-server/20-configuration.md) reference handy for CLI flags and environment variables

Start with [Netlab Configuration](10-netlab-configuration.md) if this is a fresh host, or jump straight to [Production Deployment](30-production.md) if Netlab is already working.

## What Remote Lab deliberately does not cover

Enterprise-system integration (IPAM, NetBox, ServiceNow, monitoring pipelines) is **not** part of any deployment stage -- the service keeps its scope narrow on purpose. The integration seam for those systems sits in your own pytest `conftest.py` layer, not inside the lab server. See [Resources -- Enterprise systems integration](../99-appendix/resources.md#enterprise-systems-integration) for the rationale and the specific integration points.
