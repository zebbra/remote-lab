---
page_purpose: overview
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: beginner
---

# Getting Started

Remote Lab lets you run Netlab topologies on a shared VM while keeping your test suite local. How you use it depends on your role and what infrastructure you have available.

## Test consumer (most users)

You write tests that need a live network topology. Someone else has already set up the Remote Lab server and VPN connectivity. Follow this path:

| Step | Page | Time |
|------|------|------|
| 1 | [Setup](10-setup.md) -- install the package and configure your environment | ~5 min |
| 2 | [Your First Lab Session](20-first-lab.md) -- walk through the full lifecycle with cURL | ~15 min |
| 3 | [Using Pytest Fixtures](30-pytest-fixtures.md) -- integrate Remote Lab into your test suite | ~10 min |

After completing these three pages you will be able to write pytest tests that spin up Netlab topologies on demand.

## No Remote Lab server yet? Try local mode

If you just want to see Netlab running against a topology on your own machine — no VPN, no server — call `LabManager` directly. This is the fastest path for trying out Remote Lab's topology lifecycle on your laptop. You will need [Netlab installed locally](../40-testing/20-local-testing.md#prerequisites), then follow the direct-`LabManager` example on that page.

| Step | Page | Time |
|------|------|------|
| 1 | [Local Lab Testing](../40-testing/20-local-testing.md) -- install Netlab and run `LabManager.acquire()` directly | ~5 min Netlab install + ~10 min walkthrough |

Once you're comfortable, promote your topology to a Remote Lab server using the **Test consumer** path above. The two paths use different APIs (the `remote_lab_fixture` factory is remote-only — there is no automatic fall-back to local execution).

## Server operator

You are responsible for the Remote Lab VM itself -- installing Netlab, configuring VPN access, and running the server process. Start with [Deployment](../50-deployment/index.md), which covers Netlab installation, Headscale/Tailscale VPN setup, and production configuration.

Once the server is running, come back here and walk through the test consumer path so you can verify the setup end-to-end.
