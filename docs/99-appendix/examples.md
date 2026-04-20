---
page_purpose: index
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: beginner
---

# Examples

This page indexes the runnable code examples that appear throughout the documentation. Use it to jump straight to the snippet you need.

## cURL Examples

| Example | Description | Location |
|---------|-------------|----------|
| Full session lifecycle | Create session, poll until active, upload topology, release, end session | [Your First Lab Session](../getting-started/20-first-lab.md) |
| Upload with extra files | `POST /lab` with `-F "extra_files=@path"` for supporting configs | [REST API](../20-server/10-rest-api.md), [Topology Format — extra_files](../10-concepts/40-topology-format.md#extra_files-upload-mechanism) |
| Subdirectory extra_files | `extra_files` with `filename=configs/r1.cfg` to land files under a nested path | [Topology Format — extra_files](../10-concepts/40-topology-format.md#extra_files-upload-mechanism) |
| Force-destroy a lab | `DELETE /lab?force=true` to tear down a stuck lab | [REST API](../20-server/10-rest-api.md), [Administration — Lab stuck busy](../20-server/30-administration.md#lab-stuck-busy) |
| Heartbeat keep-alive | `POST /session/heartbeat` with `X-Session-ID` header | [REST API](../20-server/10-rest-api.md) |
| Health check | `GET /healthz` liveness probe | [REST API](../20-server/10-rest-api.md) |

## Python Client Examples

| Example | Description | Location |
|---------|-------------|----------|
| Instantiate `RemoteLabClient` | Constructor with explicit timeouts | [RemoteLabClient API](../30-client/10-remote-lab-client.md) |
| Acquire and release a lab | `client.acquire()` / `client.release()` round-trip | [RemoteLabClient API](../30-client/10-remote-lab-client.md) |
| `try/finally` cleanup | Explicit `client.close()` in a `finally` block — `RemoteLabClient` does not implement the context-manager protocol. | [RemoteLabClient API](../30-client/10-remote-lab-client.md#close) |
| `destroy(force=True)` teardown | Explicit lab destruction (server-assisted cleanup) | [RemoteLabClient API](../30-client/10-remote-lab-client.md#destroyforcetrue) |
| SSH via `ansible_host` | Reach a node by the `ansible_host` field on `DeviceInfoDto.raw` | [Pytest Fixtures](../30-client/20-pytest-fixtures.md), [Getting Started — Using Pytest Fixtures](../getting-started/30-pytest-fixtures.md) |
| Environment-based configuration | Setting `REMOTE_LAB_URL` and timeout env vars | [Configuration](../20-server/20-configuration.md) |

## Pytest Fixture Examples

| Example | Description | Location |
|---------|-------------|----------|
| Declare a fixture with `remote_lab_fixture` | Factory call in `conftest.py` with `reuse_lab=True` | [Pytest Fixtures](../30-client/20-pytest-fixtures.md) |
| Use a lab fixture in a test | Test function receiving the device list | [Pytest Fixtures](../30-client/20-pytest-fixtures.md) |
| Test setup and environment | `REMOTE_LAB_URL` configuration for test suites | [Testing Setup](../40-testing/10-setup.md) |

## Topology File Examples

The examples below conform to the [Topology Format](../10-concepts/40-topology-format.md) contract — see that page for the supported provider/module/device-kind matrix.

| Example | Description | Location |
|---------|-------------|----------|
| Minimal FRR topology | Two-router OSPF topology using `provider: clab` | [Your First Lab Session](../getting-started/20-first-lab.md) |
| Two-node IOL topology | Cisco IOL topology with IOS-specific test assertions | [Cisco IOL tutorial](../40-testing/20-local-testing.md#cisco-iol-tutorial) |

## Deployment Config Examples

| Example | Description | Location |
|---------|-------------|----------|
| Headscale ACL JSON | Grouped node/tag policy for Remote Lab server + CI runners | [Headscale VPN — ACLs](../50-deployment/20-headscale-vpn.md) |

