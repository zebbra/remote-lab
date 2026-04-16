---
page_purpose: overview
personas_served: [devops-engineer, junior-network-engineer]
difficulty_level: intermediate
---

# Client

The client side of Remote Lab has two layers: a low-level HTTP client and a high-level pytest fixture factory. Most users interact exclusively with the fixture layer; the client class exists for programmatic access and serves as the transport underneath every fixture.

## In This Section

- **[RemoteLabClient API](10-remote-lab-client.md)** -- Session-aware HTTP client that handles session creation, queue waiting, lab acquisition, and teardown. Wraps `requests.Session` with retry logic, timeout configuration, and automatic session lifecycle management.

- **[Pytest Fixtures](20-pytest-fixtures.md)** -- The `remote_lab_fixture` factory and the `remote_lab_client` session-scoped fixture that powers it. Covers fixture registration, test ordering by topology rank, and environment variable configuration.

## Which Layer Do I Need?

| Scenario | Use |
|----------|-----|
| Writing pytest tests against Netlab topologies | `remote_lab_fixture` -- see [Pytest Fixtures](20-pytest-fixtures.md) |
| Building non-pytest tooling that needs lab access | `RemoteLabClient` directly -- see [RemoteLabClient API](10-remote-lab-client.md) |
| Debugging fixture behavior or timeouts | Both pages -- the fixture delegates to the client for all HTTP calls |

For a guided walkthrough of writing your first fixture-based test, see [Getting Started -- Using Pytest Fixtures](../getting-started/30-pytest-fixtures.md).
