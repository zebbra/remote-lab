---
page_purpose: overview
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: beginner
---

# Getting Started

Remote Lab lets you run Netlab topologies on a shared VM while keeping your test suite local. How you use it depends on your role.

## Test consumer (most users)

You write tests that need a live network topology. Someone else has already set up the Remote Lab server and VPN connectivity. Follow this path:

| Step | Page | Time |
|------|------|------|
| 1 | [Setup](10-setup.md) -- install the package and configure your environment | ~5 min |
| 2 | [Your First Lab Session](20-first-lab.md) -- walk through the full lifecycle with cURL | ~15 min |
| 3 | [Using Pytest Fixtures](30-pytest-fixtures.md) -- integrate Remote Lab into your test suite | ~10 min |

After completing these three pages you will be able to write pytest tests that spin up Netlab topologies on demand.

## Server operator

You are responsible for the Remote Lab VM itself -- installing Netlab, configuring VPN access, and running the server process. Start with [Deployment](../50-deployment/index.md), which covers Netlab installation, Headscale/Tailscale VPN setup, and production configuration.

Once the server is running, come back here and walk through the test consumer path so you can verify the setup end-to-end.
