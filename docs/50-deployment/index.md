---
page_purpose: overview
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: intermediate
---

# Deployment

Deploying a Remote Lab instance means preparing a VM with Netlab, networking it into your tailnet, and running the server as a long-lived process. This section covers all three concerns.

## What goes where

The Remote Lab server runs on a dedicated Linux host (physical or virtual) alongside Netlab and Containerlab. Clients -- your pytest test suites and CI runners -- reach the server over HTTP, typically through a Headscale/Tailscale VPN mesh.

| Concern | Page |
|---------|------|
| Installing and configuring Netlab + Containerlab on the host | [Netlab Configuration](10-netlab-configuration.md) |
| Setting up Headscale VPN so clients can reach lab subnets | [Headscale VPN](20-headscale-vpn.md) |
| Running the server as a systemd service, reverse proxy, TLS, monitoring, and backups | [Production Deployment](30-production.md) |

## Prerequisites

Before working through the deployment pages, you should have:

- An Ubuntu 24.04+ host with Docker installed
- Familiarity with the [Architecture](../10-concepts/10-architecture.md) and the one-lab-per-host constraint
- The server [Configuration](../20-server/20-configuration.md) reference handy for CLI flags and environment variables

Start with [Netlab Configuration](10-netlab-configuration.md) if this is a fresh host, or jump straight to [Production Deployment](30-production.md) if Netlab is already working.
