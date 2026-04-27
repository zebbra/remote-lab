---
title: Use from Python
description: The two public consumer surfaces — the pytest fixture factory (stable API) and the Python HTTP client (lower-level, for scripts and notebooks).
tags: [reference, client, testing, api]
crosslink_defines: []
crosslink_references: []
---

# Use from Python

Two Python surfaces reach the Remote Lab Manager. Both ship in the same
package — `pip install neops-remote-lab` — and you choose which to use
based on context.

**`remote_lab_fixture`** — the **stable public API**.
Imported directly by the
[Worker SDK](https://docs.neops.io/neops-worker-sdk-py/docs/)
([integration guide](https://docs.neops.io/neops-worker-sdk-py/docs/testing/30-remote-lab/));
its signature is part of a contract that survives minor and patch
releases. *If you are writing tests, this is the surface you want.*

**`RemoteLabClient`** — the **lower-level HTTP client** the fixture
wraps. Use it directly when you need to drive a lab from a script, a
notebook, or any non-pytest context.

## In this section

| Guide | What you'll learn |
|---|---|
| [Pytest Fixtures](10-pytest-fixtures.md) | `remote_lab_fixture` factory arguments, the `remote_lab_client` session-scoped fixture, the one-fixture-per-test rule, and end-to-end reuse patterns. |
| [Python Client](20-python-client.md) | `RemoteLabClient` constructor, session lifecycle, `acquire` / `release` / `destroy` / `close`, retry behaviour, and the swallow-and-log quirks. |

## What to read next

- **[Architecture](../10-concepts/10-architecture.md)** — where the client
  sits relative to the server and `LabManager`.
- **[Lab Lifecycle](../10-concepts/30-lab-lifecycle.md)** — reference
  counting and reuse semantics that `reuse_lab=True` opts into.
- **[REST API](../30-server/10-rest-api.md)** — the authoritative endpoint
  reference the Python client wraps.
- **[Configuration](../30-server/20-configuration.md)** — the environment
  variables the client reads (`REMOTE_LAB_URL` and the three timeouts).
