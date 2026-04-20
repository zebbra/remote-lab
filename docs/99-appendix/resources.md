---
page_purpose: reference
personas_served: [devops-engineer, senior-network-architect]
difficulty_level: beginner
---

# Resources

External documentation and project links relevant to Remote Lab.

## Remote Lab Project

- [PyPI -- neops-remote-lab](https://pypi.org/project/neops_remote_lab/) -- package page with version history and install instructions.
- [GitHub -- zebbra/neops-remote-lab](https://github.com/zebbra/neops-remote-lab) -- source code, issues, and CI workflows.

## Neops Ecosystem

- [neops-worker-sdk-py](https://github.com/zebbra/neops-worker-sdk-py) -- Python SDK for writing neops workers. Imports `remote_lab_fixture` directly to declare lab-backed integration tests; the fixture's call signature is the public API contract that Remote Lab maintains for this consumer.

## Network Lab Tooling

- [Netlab documentation](https://netlab.tools) -- the orchestration layer that Remote Lab wraps. Covers topology file format, providers, modules, and the `netlab` CLI.
- [Containerlab documentation](https://containerlab.dev) -- the default Netlab provider (`provider: clab`). Reference for container runtimes, node kinds, and network wiring.

## VPN and Connectivity

- [Headscale documentation](https://headscale.net/) -- self-hosted Tailscale-compatible control plane used to mesh the lab host with clients.
- [Tailscale documentation](https://tailscale.com/kb/) -- client behavior, subnet routing, ACLs, and troubleshooting for the WireGuard-based mesh VPN.

## Frameworks and Libraries

- [FastAPI documentation](https://fastapi.tiangolo.com/) -- the web framework powering the Remote Lab server. Useful for understanding OpenAPI schema generation, dependency injection, and the interactive `/docs` UI.
- [pytest documentation](https://docs.pytest.org/en/stable/) -- the test framework that hosts `remote_lab_fixture`. The [fixtures explanation](https://docs.pytest.org/en/stable/explanation/fixtures.html) is the right starting point if pytest's fixture model is new to you.
- [Python `logging` module](https://docs.python.org/3/library/logging.html) -- standard library reference for the structured logging the server emits. Relevant when writing custom `--log-config` YAML files.

## Enterprise systems integration

Remote Lab does not ship integrations with enterprise network systems (IPAM, ServiceNow, NetBox, external monitoring platforms). There is no built-in way to pull a topology from NetBox, push a lab-run result into a change ticket, or report lab metrics into an APM. This is deliberate: the service's scope is the lab host itself -- its REST surface, the Netlab lifecycle, and the session queue -- and keeping that scope narrow is how the code stays small enough to audit.

### What this means for integration

- **For observability**, treat Remote Lab the same as any other HTTP service: scrape `/debug/health` from your monitoring stack and ship journald logs where you already ship them. The [Production -- Monitoring](../50-deployment/30-production.md#monitoring) section has a Prometheus/Grafana/Loki recipe you can adapt.
- **For topology sourcing**, any enterprise lookup (IPAM, NetBox, inventory APIs) happens *before* the topology YAML reaches Remote Lab. The service accepts whatever `.yml` file you upload; how you generated it is not its concern.
- **For test-level integration points**, the right seam is a pytest `conftest.py` hook in your own test project. Fetch whatever you need from enterprise systems there (credentials, expected facts, change-ticket IDs) and pass it into your tests via standard pytest fixtures alongside the `remote_lab_fixture`. Remote Lab itself stays unaware of those external systems.

If you need tighter coupling -- for example, a lab run that automatically opens a change ticket on failure -- build that outside Remote Lab (in the same conftest layer or in a CI-pipeline step that wraps `pytest`). Keeping the lab service free of those hooks is what lets it be upgraded, restarted, or replaced without coordinating with every consuming team.

