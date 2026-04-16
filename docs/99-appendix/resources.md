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

